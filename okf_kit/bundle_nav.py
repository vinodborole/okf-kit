"""Bundle navigation primitives shared by chat and the MCP server.

These are the tools an agent uses to walk an OKF bundle — the same
list_directory / read_concept pair proven to let independent agents navigate
calknowledge bundles, plus a no-index keyword search. All are
path-traversal-guarded.
"""

from __future__ import annotations

import re
from pathlib import Path

from .config import STATE_DIRNAME
from .okf import RESERVED

MAX_FILE_CHARS = 12000
_TOKEN = re.compile(r"[a-z0-9]{2,}")


def _safe(bundle_dir: Path, path: str) -> Path | None:
    target = (bundle_dir / path.strip().lstrip("/")).resolve()
    root = bundle_dir.resolve()
    if target == root or root in target.parents:
        return target
    return None


def list_directory(bundle_dir, path: str = "/") -> str:
    bundle_dir = Path(bundle_dir)
    target = _safe(bundle_dir, path)
    if not target or not target.is_dir():
        return f"error: {path} is not a directory in this bundle. Try /index.md."
    entries = sorted(
        ("dir:  " if p.is_dir() else "file: ") + p.name
        for p in target.iterdir()
        if p.name != STATE_DIRNAME
    )
    return "\n".join(entries) or "(empty)"


def read_concept(bundle_dir, path: str) -> str:
    bundle_dir = Path(bundle_dir)
    target = _safe(bundle_dir, path)
    if not target or not target.is_file():
        return f"error: {path} is not a file in this bundle. Read /index.md to see what exists."
    return target.read_text(encoding="utf8")[:MAX_FILE_CHARS]


def _concept_files(bundle_dir: Path):
    for md in (bundle_dir / "pages").rglob("*.md"):
        if md.name not in RESERVED:
            yield md


def _split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (title, body-without-frontmatter)."""
    title = None
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            fm = text[4:end]
            m = re.search(r"^title:\s*(.+)$", fm, re.MULTILINE)
            if m:
                title = m.group(1).strip()
            body = text[end + 5 :]
    return title, body


def search_bundle(bundle_dir, query: str, limit: int = 5) -> list[dict]:
    """Keyword search over concept files (title-boosted). No index needed."""
    bundle_dir = Path(bundle_dir)
    terms = set(_TOKEN.findall(query.lower()))
    if not terms:
        return []
    results = []
    for md in _concept_files(bundle_dir):
        title, body = _split_frontmatter(md.read_text(encoding="utf8"))
        body_l = body.lower()
        title_l = (title or "").lower()
        score = sum(body_l.count(t) + 3 * title_l.count(t) for t in terms)
        if score:
            rel = "/" + str(md.relative_to(bundle_dir))
            results.append({"path": rel, "title": title, "score": score,
                            "snippet": _snippet(body, terms)})
    results.sort(key=lambda r: -r["score"])
    return results[:limit]


def _snippet(text: str, terms: set[str], width: int = 220) -> str:
    lower = text.lower()
    pos = min((lower.find(t) for t in terms if lower.find(t) >= 0), default=-1)
    if pos < 0:
        return ""
    start = max(0, pos - width // 3)
    return re.sub(r"\s+", " ", text[start : start + width]).strip()
