"""Zero-key fallback: answer from keyword retrieval with citations.

When no LLM provider is configured, `okf chat` still does something useful —
it returns the most relevant concepts with their matching passages quoted and
cited, clearly labeled as retrieval-only. (Adopted from the deterministic
`ask` in bushans/okfgen; see docs/ECOSYSTEM.md.)
"""

from __future__ import annotations

from pathlib import Path

from ..bundle_nav import search_bundle


def answer(bundle_dir, question: str, *, limit: int = 3) -> dict:
    bundle_dir = Path(bundle_dir)
    hits = search_bundle(bundle_dir, question, limit=limit)
    if not hits:
        return {
            "answer": "No matching content found in this bundle (retrieval-only, no LLM configured).",
            "steps": [{"tool": "search_bundle", "path": question}],
            "sources": [],
        }
    lines = ["Retrieval-only answer (no LLM configured) — most relevant concepts:\n"]
    for i, h in enumerate(hits, 1):
        title = h["title"] or h["path"]
        lines.append(f"{i}. {title}  [{h['path']}]")
        lines.append(f"   {h['snippet']}\n")
    lines.append("Configure a provider for a synthesized answer:  okf chat <bundle> --provider ollama")
    return {
        "answer": "\n".join(lines),
        "steps": [{"tool": "search_bundle", "path": question}],
        "sources": [h["path"] for h in hits],
    }
