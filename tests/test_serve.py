"""Tests for `okf serve` — the local API. Runs fully offline (provider 'none'
uses zero-key retrieval). Keyring is forced to the fail backend so key storage
deterministically uses the 0600 file fallback.
"""

from __future__ import annotations

import json
import os

import pytest

pytest.importorskip("fastapi", reason="needs the [serve] extra")

# Force keyring to fail → settings uses the file fallback (deterministic, headless-safe).
os.environ["PYTHON_KEYRING_BACKEND"] = "keyring.backends.fail.Keyring"

TOKEN = "test-token-abc"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("OKF_HOME", str(tmp_path / "okf"))
    from fastapi.testclient import TestClient

    from okf_kit.serve.app import create_app

    # a tiny installed bundle
    b = tmp_path / "okf" / "bundles" / "testbook"
    (b / "pages").mkdir(parents=True)
    (b / "index.md").write_text("---\ntype: Index\ntitle: Test Book\n---\n- pages\n", encoding="utf8")
    (b / "pages" / "intro.md").write_text(
        "---\ntype: Web Page\ntitle: Introduction\n---\n# Introduction\n\nWelcome.\n", encoding="utf8"
    )
    (b / "pages" / "ownership.md").write_text(
        "---\ntype: Web Page\ntitle: Ownership\nresource: https://doc.rust-lang.org/book/ch04-01.html\n---\n"
        "# Ownership\n\n## Borrowing\n\nOwnership means every value has exactly one owner.\n",
        encoding="utf8",
    )
    (b / ".okf-kit").mkdir()
    (b / ".okf-kit" / "state.json").write_text(
        json.dumps({"root_url": "https://example.com/book", "page_count": 2,
                    "updated_at": "2026-07-08T00:00:00Z"}),
        encoding="utf8",
    )
    return TestClient(create_app(TOKEN))


def test_auth_required(client):
    assert client.get("/api/health").status_code == 401
    r = client.get("/api/health", headers=AUTH)
    assert r.status_code == 200 and r.json()["ok"] is True


def test_status_none_provider_online(client):
    r = client.get("/api/status", headers=AUTH).json()
    assert r["provider"] == "none" and r["online"] is True


def test_books_and_delete(client):
    books = client.get("/api/books", headers=AUTH).json()
    assert len(books) == 1
    bk = books[0]
    assert bk["name"] == "testbook" and bk["title"] == "Test Book" and bk["pages"] == 2
    assert client.get("/api/books/nope", headers=AUTH).status_code == 404
    assert client.delete("/api/books/testbook", headers=AUTH).json() == {"removed": True}
    assert client.get("/api/books", headers=AUTH).json() == []


def test_toc_and_concept(client):
    toc = client.get("/api/books/testbook/toc", headers=AUTH).json()
    ids = _concept_ids(toc)
    assert "pages/intro" in ids and "pages/ownership" in ids
    # toc carries each concept's original URL so a GUI can map links → concepts
    own = _find_concept(toc, "pages/ownership")
    assert own["resource"] == "https://doc.rust-lang.org/book/ch04-01.html"

    c = client.get("/api/books/testbook/concept", params={"id": "pages/ownership"}, headers=AUTH).json()
    assert c["title"] == "Ownership"
    assert "one owner" in c["markdown"]
    assert {"level": 2, "text": "Borrowing", "id": "borrowing"} in c["headings"]
    assert c["prev"]["id"] == "pages/intro" and c["next"] is None

    assert client.get("/api/books/testbook/concept", params={"id": "pages/nope"},
                      headers=AUTH).status_code == 404


def test_chat_retrieval_flow(client):
    sid = client.post("/api/books/testbook/chats", headers=AUTH).json()["id"]
    r = client.post(f"/api/books/testbook/chats/{sid}/ask",
                    json={"question": "what is ownership?"}, headers=AUTH)
    assert r.status_code == 200
    events = _parse_sse(r.text)
    assert any(e[0] == "token" for e in events)
    sources = next(e[1] for e in events if e[0] == "sources")["sources"]
    assert any(s["concept_id"] == "pages/ownership" for s in sources)
    # citation is deep-linkable
    own = next(s for s in sources if s["concept_id"] == "pages/ownership")
    assert own["anchor"] in ("ownership", "borrowing")
    assert any(e[0] == "done" for e in events)

    # persisted + listable
    chats = client.get("/api/books/testbook/chats", headers=AUTH).json()
    assert len(chats) == 1 and chats[0]["id"] == sid
    convo = client.get(f"/api/books/testbook/chats/{sid}", headers=AUTH).json()
    assert convo["messages"][0]["role"] == "user"
    assert convo["messages"][1]["role"] == "assistant"
    assert client.delete(f"/api/books/testbook/chats/{sid}", headers=AUTH).json() == {"removed": True}


def test_settings_roundtrip_key_in_fallback(client):
    r = client.put("/api/settings", json={"provider": "openai", "model": "gpt-4o", "api_key": "sk-xyz"},
                   headers=AUTH).json()
    assert r == {"provider": "openai", "model": "gpt-4o", "base_url": None, "has_key": True}
    got = client.get("/api/settings", headers=AUTH).json()
    assert got["has_key"] is True and "api_key" not in got  # key never returned
    assert client.put("/api/settings", json={"provider": "bogus"}, headers=AUTH).status_code == 400


def _concept_ids(nodes):
    out = []
    for n in nodes:
        if n["kind"] == "concept":
            out.append(n["id"])
        else:
            out += _concept_ids(n["children"])
    return out


def _find_concept(nodes, cid):
    for n in nodes:
        if n["kind"] == "concept" and n["id"] == cid:
            return n
        if n["kind"] == "section":
            found = _find_concept(n["children"], cid)
            if found:
                return found
    return None


def _parse_sse(text):
    events = []
    for block in text.strip().split("\n\n"):
        ev, data = None, None
        for line in block.splitlines():
            if line.startswith("event: "):
                ev = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
        if ev:
            events.append((ev, data))
    return events
