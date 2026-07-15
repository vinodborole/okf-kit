"""The local API surface for `okf serve` (spec: OKF-SERVE-SPEC.md).

Every route reuses existing okf-kit functions — registry, bundle_reader,
bundle_nav, chat.* — and adds only the HTTP layer + SSE. Loopback + a per-launch
bearer token guard everything under /api.

NB: intentionally no `from __future__ import annotations` — FastAPI resolves the
`Request` type hint at definition time, and PEP 563 stringized hints break that
for locally-imported types.
"""

import hmac
import io
import json
import os
import time

from .. import __version__
from ..config import bundles_dir, chats_dir, home_dir
from ..bundle_reader import _split_frontmatter
from ..chat import agent, retrieval
from ..chat.history import History
from ..chat.providers import describe_provider_error, make_provider
from ..model import utcnow_iso
from ..registry import DEFAULT_REGISTRY, _extract_zip, load_registry, local_bundles
from ..okf import validate_bundle
from . import reader, settings as settings_mod

_API = "0"
_registry_cache: dict = {"at": 0.0, "entries": None}
_REGISTRY_TTL = 300  # seconds


def create_app(token: str, ui_dir: str | None = None):
    from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request
    from fastapi.responses import JSONResponse, StreamingResponse
    from starlette.concurrency import run_in_threadpool

    app = FastAPI(title="okf serve", version=__version__)

    def require_token(request: Request):
        got = ""
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            got = auth[7:].strip()
        got = got or request.query_params.get("token", "")
        if not (got and hmac.compare_digest(got, token)):
            raise HTTPException(status_code=401, detail="missing or invalid token")

    guard = [Depends(require_token)]

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    # ---- system -----------------------------------------------------------
    @app.get("/api/health")
    def health(_=guard[0]):
        return {"ok": True, "version": __version__, "okf_home": str(home_dir()), "api": _API}

    @app.get("/api/status")
    def status(_=guard[0]):
        s = settings_mod.load_settings()
        return {"provider": s["provider"], "model": s["model"], "online": _provider_online(s)}

    # ---- registry (Discover) ---------------------------------------------
    @app.get("/api/registry")
    async def registry_ep(_=guard[0]):
        now = time.monotonic()
        if _registry_cache["entries"] is None or now - _registry_cache["at"] > _REGISTRY_TTL:
            try:
                _registry_cache["entries"] = await run_in_threadpool(load_registry, DEFAULT_REGISTRY)
                _registry_cache["at"] = now
            except (Exception, SystemExit) as exc:  # offline / bad registry: report, don't 500
                raise HTTPException(status_code=502, detail=f"can't reach registry: {exc}") from exc
        installed = {b["name"] for b in local_bundles()}
        entries = [
            {
                "name": e.get("name"),
                "title": e.get("title") or _prettify(e.get("name", "")),
                "source_url": e.get("source_url"),
                "publisher": e.get("publisher"),
                "category": e.get("category"),
                "tag": (e.get("name") or "").split("-")[0],
                "pages": e.get("pages"),
                "license": e.get("license"),
                "description": e.get("description"),
                "installed": e.get("name") in installed,
            }
            for e in _registry_cache["entries"]
        ]
        return {"fetched_at": utcnow_iso(), "entries": entries}

    # ---- library (books) --------------------------------------------------
    @app.get("/api/books")
    def books(_=guard[0]):
        return [_book_view(b["name"]) for b in local_bundles()]

    @app.get("/api/books/{name}")
    def book(name: str, _=guard[0]):
        v = _book_view(name)
        if not v:
            raise HTTPException(status_code=404, detail=f"'{name}' is not installed")
        return v

    @app.post("/api/books/{name}/install")
    async def install(name: str, _=guard[0]):
        async def gen():
            try:
                entries = await run_in_threadpool(load_registry, DEFAULT_REGISTRY)
                entry = next((e for e in entries if e.get("name") == name), None)
                if not entry or not entry.get("download"):
                    yield sse("error", {"message": f"'{name}' is not in the registry"})
                    return
                yield sse("progress", {"phase": "downloading"})
                data = await run_in_threadpool(_download, entry["download"])
                yield sse("progress", {"phase": "extracting"})
                dest = bundles_dir() / name
                await run_in_threadpool(_extract_zip, io.BytesIO(data), dest)
                yield sse("progress", {"phase": "validating"})
                ok = await run_in_threadpool(validate_bundle, dest, quiet=True)
                yield sse("done", {"book": _book_view(name), "conformant": bool(ok)})
            except (Exception, SystemExit) as exc:
                yield sse("error", {"message": str(exc)})

        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.delete("/api/books/{name}")
    def remove(name: str, _=guard[0]):
        import shutil

        d = bundles_dir() / name
        if not d.exists():
            raise HTTPException(status_code=404, detail=f"'{name}' is not installed")
        shutil.rmtree(d)
        chats = chats_dir() / name
        if chats.exists():
            shutil.rmtree(chats)
        return {"removed": True}

    # ---- read -------------------------------------------------------------
    @app.get("/api/books/{name}/toc")
    def toc(name: str, _=guard[0]):
        d = _bundle_or_404(name)
        return reader.build_toc(reader.ordered_concepts(d))

    @app.get("/api/books/{name}/concept")
    def concept(name: str, id: str = Query(...), _=guard[0]):
        d = _bundle_or_404(name)
        view = reader.concept_view(d, id.lstrip("/"), reader.ordered_concepts(d))
        if not view:
            raise HTTPException(status_code=404, detail=f"no concept '{id}' in '{name}'")
        return view

    # ---- chat -------------------------------------------------------------
    @app.get("/api/books/{name}/chats")
    def list_chats(name: str, _=guard[0]):
        return _list_chats(name)

    @app.post("/api/books/{name}/chats")
    def new_chat(name: str, _=guard[0]):
        h = History(name)  # fresh timestamped session id; file created on first turn
        return {"id": h.path.stem, "title": "New chat"}

    @app.get("/api/books/{name}/chats/{sid}")
    def get_chat(name: str, sid: str, _=guard[0]):
        return _get_chat(name, sid)

    @app.delete("/api/books/{name}/chats/{sid}")
    def del_chat(name: str, sid: str, _=guard[0]):
        f = chats_dir() / name / f"{sid}.jsonl"
        if not f.exists():
            raise HTTPException(status_code=404, detail="no such chat")
        f.unlink()
        return {"removed": True}

    @app.post("/api/books/{name}/chats/{sid}/ask")
    async def ask(name: str, sid: str, payload: dict = Body(...), _=guard[0]):
        bundle = _bundle_or_404(name)
        question = (payload or {}).get("question", "").strip()
        if not question:
            raise HTTPException(status_code=400, detail="question is required")
        s = settings_mod.load_settings()

        async def gen():
            try:
                result = await run_in_threadpool(_run_ask, bundle, name, sid, question, s)
            except (Exception, SystemExit) as exc:  # SystemExit: a missing extra must not kill the server
                yield sse("error", {"message": describe_provider_error(exc, s["provider"], s["model"])})
                return
            for chunk in _chunks(result["answer"]):
                yield sse("token", {"text": chunk})
            yield sse("sources", {"sources": result["sources"]})
            yield sse("done", {"message": result["message"]})

        return StreamingResponse(gen(), media_type="text/event-stream")

    # ---- settings ---------------------------------------------------------
    @app.get("/api/settings")
    def get_settings(_=guard[0]):
        return settings_mod.public_settings()

    @app.put("/api/settings")
    def put_settings(payload: dict = Body(...), _=guard[0]):
        provider = (payload or {}).get("provider", "none")
        if provider not in ("none", "ollama", "openai", "openrouter", "anthropic", "custom"):
            raise HTTPException(status_code=400, detail=f"unknown provider '{provider}'")
        return settings_mod.save_settings(
            provider, payload.get("model"), payload.get("base_url"), payload.get("api_key")
        )

    @app.post("/api/shutdown")
    def shutdown(_=guard[0]):
        import threading

        threading.Timer(0.2, lambda: os._exit(0)).start()
        return {"shutting_down": True}

    # ---- optional static UI ----------------------------------------------
    if ui_dir and os.path.isdir(ui_dir):
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=ui_dir, html=True), name="ui")

    @app.exception_handler(HTTPException)
    async def _err(request, exc):  # uniform error shape
        code = {400: "bad_request", 401: "unauthorized", 404: "not_found",
                409: "conflict", 502: "upstream"}.get(exc.status_code, "error")
        return JSONResponse(status_code=exc.status_code,
                            content={"error": {"code": code, "message": exc.detail}})

    return app


# ---- helpers (pure, testable) --------------------------------------------

def _bundle_or_404(name: str):
    from fastapi import HTTPException

    d = bundles_dir() / name
    if not (d / "index.md").exists():
        raise HTTPException(status_code=404, detail=f"'{name}' is not installed")
    return d


def _book_view(name: str) -> dict | None:
    d = bundles_dir() / name
    sf = d / ".okf-kit" / "state.json"
    if not sf.exists():
        return None
    s = json.loads(sf.read_text(encoding="utf8"))
    size = sum(f.stat().st_size for f in d.rglob("*.md"))
    chats = chats_dir() / name
    chat_count = len(list(chats.glob("*.jsonl"))) if chats.exists() else 0
    synced = (s.get("last_sync") or {}).get("synced_at") or s.get("updated_at") or ""
    return {
        "name": name,
        "title": _book_title(d, name, s),
        "source_url": s.get("root_url"),
        "tag": name.split("-")[0],
        "pages": s.get("page_count"),
        "size_bytes": size,
        "synced_at": synced,
        "conformant": True,
        "chat_count": chat_count,
    }


def _book_title(d, name: str, state: dict) -> str:
    for k in ("title", "site_name"):
        if state.get(k):
            return state[k]
    for fn in ("index.md", "home.md"):
        f = d / fn
        if f.exists():
            fm, _ = _split_frontmatter(f.read_text(encoding="utf8"))
            if fm.get("title"):
                return fm["title"]
    return _prettify(name)


def _list_chats(name: str) -> list[dict]:
    dd = chats_dir() / name
    out = []
    for f in sorted(dd.glob("*.jsonl")) if dd.exists() else []:
        recs = [json.loads(x) for x in f.read_text(encoding="utf8").splitlines() if x.strip()]
        users = [r for r in recs if r.get("role") == "user"]
        title = (users[0]["content"][:48] if users else "New chat")
        out.append({
            "id": f.stem,
            "title": title,
            "updated_at": recs[-1]["ts"] if recs else "",
            "message_count": len(recs),
        })
    out.sort(key=lambda x: x["updated_at"], reverse=True)
    return out


def _get_chat(name: str, sid: str) -> dict:
    recs = History(name, session=sid).load()
    messages = [
        {"role": r["role"], "text": r["content"],
         "sources": (r.get("meta") or {}).get("sources"), "ts": r["ts"]}
        for r in recs
    ]
    title = next((m["text"][:48] for m in messages if m["role"] == "user"), "New chat")
    return {"id": sid, "title": title, "messages": messages}


def _run_ask(bundle, name: str, sid: str, question: str, s: dict) -> dict:
    provider = _provider_from(s)
    if provider is None:
        res = retrieval.answer(bundle, question)
    else:
        res = agent.ask(bundle, question, provider)
    sources = reader.enrich_sources(bundle, res.get("sources", []), question)
    hist = History(name, session=sid)
    hist.append("user", question)
    hist.append("assistant", res["answer"], meta={"sources": sources})
    message = {"role": "assistant", "text": res["answer"], "sources": sources, "ts": utcnow_iso()}
    return {"answer": res["answer"], "sources": sources, "message": message}


def _provider_from(s: dict):
    if s["provider"] in (None, "none"):
        return None
    key = settings_mod.get_key(s["provider"])
    return make_provider(s["provider"], s.get("model"), s.get("base_url"), api_key=key)


def _provider_online(s: dict) -> bool:
    provider = s["provider"]
    if provider in (None, "none"):
        return True  # retrieval always works
    if provider == "ollama":
        import httpx

        base = s.get("base_url") or "http://localhost:11434/v1"
        try:
            httpx.get(base.rsplit("/v1", 1)[0] + "/api/tags", timeout=1.5).raise_for_status()
            return True
        except Exception:  # noqa: BLE001
            return False
    return bool(settings_mod.get_key(provider))  # hosted: treat "has key" as ready


def _download(url: str) -> bytes:
    import httpx

    return httpx.get(url, follow_redirects=True, timeout=120).raise_for_status().content


def _chunks(text: str, size: int = 24):
    """Chunk a finished answer for a typewriter reveal over SSE (true token
    streaming is a v1 provider change)."""
    words = text.split(" ")
    buf = ""
    for w in words:
        buf += w + " "
        if len(buf) >= size:
            yield buf
            buf = ""
    if buf:
        yield buf


def _prettify(name: str) -> str:
    import re

    return re.sub(r"[-_]+", " ", name).strip().title() or name
