"""Read-side helpers for `okf serve`: a Contents tree, a single concept view
(markdown + heading anchors + prev/next), and citation-source enrichment that
turns a bare concept path into `{concept_id, title, section, anchor, snippet}`
for the clickable chat chip. Anchors are GitHub-style slugs so the UI's rendered
headings line up with citation links.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..bundle_reader import _split_frontmatter  # (dict, body)
from ..okf import RESERVED

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$")
_TOKEN = re.compile(r"[a-z0-9]{2,}")


def slug(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"[\s_]+", "-", s).strip("-")


def ordered_concepts(bundle_dir) -> list[dict]:
    """Every concept as {id, title}, in bundle path order (drives TOC + prev/next)."""
    root = Path(bundle_dir)
    files = sorted(
        p for p in root.rglob("*.md")
        if p.name not in RESERVED and ".okf-kit" not in p.parts
    )
    out = []
    for p in files:
        cid = p.relative_to(root).as_posix()[:-3]
        fm, _ = _split_frontmatter(p.read_text(encoding="utf8"))
        out.append({"id": cid, "title": fm.get("title") or cid.split("/")[-1]})
    return out


def build_toc(concepts: list[dict]) -> list[dict]:
    """Nest concepts into a Contents tree; collapse a single common prefix (e.g. pages/)."""
    tree: dict = {}
    for c in concepts:
        parts = c["id"].split("/")
        cur = tree
        for part in parts[:-1]:
            cur = cur.setdefault(("dir", part), {})
        cur[("file", parts[-1])] = c

    def to_list(node: dict) -> list[dict]:
        items = []
        for (kind, name), val in node.items():
            if kind == "file":
                items.append({"kind": "concept", "id": val["id"], "title": val["title"]})
            else:
                items.append({"kind": "section", "title": _prettify(name), "children": to_list(val)})
        return items

    result = to_list(tree)
    while len(result) == 1 and result[0].get("kind") == "section":  # drop a lone wrapper dir
        result = result[0]["children"]
    return result


def concept_view(bundle_dir, cid: str, ordered: list[dict]) -> dict | None:
    path = Path(bundle_dir) / (cid + ".md")
    if not path.is_file():
        return None
    fm, body = _split_frontmatter(path.read_text(encoding="utf8"))
    headings = [
        {"level": len(m.group(1)), "text": m.group(2).strip(), "id": slug(m.group(2))}
        for line in body.splitlines()
        if (m := _HEADING.match(line))
    ]
    ids = [c["id"] for c in ordered]
    i = ids.index(cid) if cid in ids else -1
    prev = ordered[i - 1] if i > 0 else None
    nxt = ordered[i + 1] if 0 <= i < len(ordered) - 1 else None
    tags = fm.get("tags") or []
    return {
        "id": cid,
        "title": fm.get("title") or cid.split("/")[-1],
        "type": fm.get("type") or "",
        "tags": tags if isinstance(tags, list) else [str(tags)],
        "resource": fm.get("resource") or "",
        "markdown": body,
        "headings": headings,
        "prev": {"id": prev["id"], "title": prev["title"]} if prev else None,
        "next": {"id": nxt["id"], "title": nxt["title"]} if nxt else None,
    }


def enrich_sources(bundle_dir, source_paths: list[str], question: str) -> list[dict]:
    """Resolve chat source paths to deep-linkable citations."""
    terms = set(_TOKEN.findall(question.lower()))
    out, seen = [], set()
    for sp in source_paths:
        cid = sp.strip().lstrip("/")
        if cid.endswith(".md"):
            cid = cid[:-3]
        if cid in seen:
            continue
        seen.add(cid)
        path = Path(bundle_dir) / (cid + ".md")
        if not path.is_file():  # e.g. the agent listed /index.md — not a concept
            continue
        fm, body = _split_frontmatter(path.read_text(encoding="utf8"))
        section, anchor, snippet = _best_section(body, terms)
        out.append({
            "concept_id": cid,
            "title": fm.get("title") or cid.split("/")[-1],
            "section": section or (fm.get("title") or cid.split("/")[-1]),
            "anchor": anchor,
            "snippet": snippet,
        })
    return out


def _best_section(body: str, terms: set[str]) -> tuple[str | None, str, str]:
    lines = body.splitlines()
    best_i, best_score = -1, 0
    for i, line in enumerate(lines):
        low = line.lower()
        score = sum(low.count(t) for t in terms)
        if score > best_score:
            best_score, best_i = score, i
    if best_i < 0:
        return None, "", _clean(" ".join(lines[:3]))[:220]
    section, anchor = None, ""
    for j in range(best_i, -1, -1):
        m = _HEADING.match(lines[j])
        if m:
            section = m.group(2).strip()
            anchor = slug(section)
            break
    return section, anchor, _clean(" ".join(lines[best_i:best_i + 3]))[:220]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _prettify(name: str) -> str:
    return re.sub(r"[-_]+", " ", name).strip() or name
