"""Read *any* OKF bundle into concepts + edges — independent of okf-kit's own
`state.json`. Edges come from concept-to-concept markdown links in the bodies
(the spec's link graph), plus okf-kit's recorded edges when present (its bodies
keep the original web links rather than concept paths). This is what lets
`visualize` consume bundles produced by any OKF tool, e.g. Google's reference
agent.
"""

from __future__ import annotations

import json
import posixpath
import re
from pathlib import Path

import yaml

RESERVED = {"index.md", "log.md"}
_LINK = re.compile(r"\]\(\s*([^)\s]+)")


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            fm = yaml.safe_load(text[4:end])
            body = text[end + 4:].lstrip("\n")
            return (fm if isinstance(fm, dict) else {}), body
    return {}, text


def _target_id(target: str, from_id: str) -> str | None:
    """Resolve a markdown link target to a concept id (bundle-relative, no .md)."""
    t = target.split("#", 1)[0].split("?", 1)[0].strip().strip("'\"")
    if not t.endswith(".md"):
        return None
    if t.startswith("/"):
        path = t[1:]
    else:
        path = posixpath.normpath(posixpath.join(posixpath.dirname(from_id), t))
    if path.startswith("..") or path.startswith("/"):
        return None
    return path[:-3]  # strip .md


def read_bundle(bundle_dir) -> dict:
    """Return {concepts: [...], edges: [[src_id, dst_id], ...]} for a bundle."""
    root = Path(bundle_dir)
    files = sorted(
        p for p in root.rglob("*.md")
        if p.name not in RESERVED and ".okf-kit" not in p.parts
    )
    concepts: list[dict] = []
    index: dict[str, int] = {}
    for p in files:
        cid = p.relative_to(root).as_posix()[:-3]  # drop .md
        fm, body = _split_frontmatter(p.read_text(encoding="utf8"))
        tags = fm.get("tags") or []
        concepts.append({
            "id": cid,
            "title": fm.get("title") or cid.split("/")[-1],
            "type": fm.get("type") or "",
            "tags": tags if isinstance(tags, list) else [str(tags)],
            "resource": fm.get("resource") or "",
            "description": fm.get("description") or "",
            "body": body,
        })
        index[cid] = len(concepts) - 1

    edges: set[tuple[str, str]] = set()
    for c in concepts:
        for m in _LINK.finditer(c["body"]):
            tid = _target_id(m.group(1), c["id"])
            if tid is not None and tid in index and tid != c["id"]:
                edges.add((c["id"], tid))

    # okf-kit's own bundles record edges in state.json (bodies keep web links)
    sf = root / ".okf-kit" / "state.json"
    if sf.exists():
        try:
            for s, t in json.loads(sf.read_text(encoding="utf8")).get("edges", []):
                sid = s[:-3] if s.endswith(".md") else s
                tid = t[:-3] if t.endswith(".md") else t
                if sid in index and tid in index and sid != tid:
                    edges.add((sid, tid))
        except Exception:  # noqa: BLE001 — a malformed state file just means no extra edges
            pass

    return {"concepts": concepts, "edges": [list(e) for e in sorted(edges)]}
