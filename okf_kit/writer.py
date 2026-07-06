"""Write crawled pages into an OKF bundle directory.

The output directory *is* the bundle:

    <bundle>/
        index.md                 root directory listing (reserved)
        log.md                   generation/sync history (reserved, appended)
        pages/                   one concept per page (frontmatter + body)
            index.md
            home.md
            docs/...
        .okf-kit/state.json      crawl config + per-page content hashes (sync)

These are module functions (not a class) so `build` and `sync` share exactly
the same concept-writing and metadata logic.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

from .config import STATE_DIRNAME, STATE_FILENAME
from .mapper import url_to_relpath
from .model import Page, PageRecord, content_hash, utcnow_iso
from .okf import (
    dodge_reserved,
    frontmatter,
    write_directory_indexes,
    write_root_index,
)


def bundle_path_for(url: str) -> str:
    """Bundle-relative concept path for a URL, e.g. 'pages/docs/intro.md'."""
    rel = dodge_reserved(url_to_relpath(url).with_suffix(".md"))
    return str(PurePosixPath("pages") / rel)


def write_concept(bundle_dir: Path, page: Page, timestamp: str) -> PageRecord | None:
    """Write one page as an OKF concept file; returns its record (or None if
    the page has no body)."""
    body = page.markdown.strip()
    if not body:
        return None
    path = bundle_path_for(page.url)
    fm = frontmatter(
        {
            "type": "Web Page",
            "title": page.title,
            "description": page.description,
            "resource": page.url,
            "timestamp": timestamp,
        }
    )
    content = f"{fm}\n{body}\n\n# Citations\n\n1. Source page: {page.url}\n"
    dest = Path(bundle_dir) / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf8")
    return PageRecord(path=path, url=page.url, title=page.title,
                      content_hash=content_hash(page.markdown))


def prune_empty_dirs(root: Path) -> None:
    for d in sorted((p for p in root.rglob("*") if p.is_dir()), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()


def append_log(bundle_dir: Path, lines: list[str]) -> None:
    log = Path(bundle_dir) / "log.md"
    existing = log.read_text(encoding="utf8") if log.exists() else "# Log\n"
    section = f"\n## {utcnow_iso()[:10]}\n\n" + "".join(f"- {line}\n" for line in lines)
    log.write_text(existing.rstrip() + "\n" + section, encoding="utf8")


def write_bundle_meta(
    bundle_dir: Path,
    records: list[PageRecord],
    *,
    root_url: str,
    config: dict,
    log_lines: list[str],
    last_sync: dict | None = None,
) -> None:
    """Directory indexes + root index + log + state.json for the full set of
    current pages."""
    bundle_dir = Path(bundle_dir)
    entries = {
        PurePosixPath(r.path): (r.title or PurePosixPath(r.path).stem) for r in records
    }
    write_directory_indexes(bundle_dir, entries)
    write_root_index(bundle_dir, root_url, len(records))
    append_log(bundle_dir, log_lines)

    state_dir = bundle_dir / STATE_DIRNAME
    state_dir.mkdir(exist_ok=True)
    state = {
        "generator": "okf-kit",
        "okf_version": "0.1",
        "root_url": root_url,
        "updated_at": utcnow_iso(),
        "config": config,
        "page_count": len(records),
        "pages": [
            {"path": r.path, "url": r.url, "title": r.title, "hash": r.content_hash}
            for r in sorted(records, key=lambda r: r.path)
        ],
    }
    if last_sync is not None:
        state["last_sync"] = last_sync
    (state_dir / STATE_FILENAME).write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf8"
    )
