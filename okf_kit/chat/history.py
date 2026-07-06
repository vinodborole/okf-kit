"""Local chat history: one JSONL session file per conversation.

Stored under ~/.okf/chats/<bundle>/<timestamp>.jsonl — nothing leaves the
machine except the provider call itself.
"""

from __future__ import annotations

import json

from ..config import chats_dir
from ..model import utcnow_iso


class History:
    def __init__(self, bundle_name: str, session: str | None = None):
        self.dir = chats_dir() / bundle_name
        self.dir.mkdir(parents=True, exist_ok=True)
        if session:
            self.path = self.dir / f"{session}.jsonl"
        else:
            self.path = self.dir / f"{utcnow_iso().replace(':', '-')}.jsonl"

    def append(self, role: str, content: str, meta: dict | None = None) -> None:
        rec = {"ts": utcnow_iso(), "role": role, "content": content}
        if meta:
            rec["meta"] = meta
        with self.path.open("a", encoding="utf8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf8").splitlines() if line.strip()]

    @classmethod
    def latest(cls, bundle_name: str) -> "History | None":
        d = chats_dir() / bundle_name
        sessions = sorted(d.glob("*.jsonl")) if d.exists() else []
        if not sessions:
            return None
        return cls(bundle_name, session=sessions[-1].stem)

    @classmethod
    def list_sessions(cls, bundle_name: str) -> list[tuple[str, int]]:
        d = chats_dir() / bundle_name
        out = []
        for f in sorted(d.glob("*.jsonl")) if d.exists() else []:
            turns = sum(1 for line in f.read_text(encoding="utf8").splitlines() if '"role": "user"' in line)
            out.append((f.stem, turns))
        return out
