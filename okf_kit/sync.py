"""Incremental re-crawl (`okf sync`): update only what changed.

Reads the bundle's `.okf-kit/state.json`, re-crawls the same root URL, diffs
page content hashes, and applies just the delta:

  added    new pages          -> written
  changed  content differs    -> rewritten (fresh timestamp)
  removed  gone from the site  -> concept file deleted
  unchanged                    -> left byte-for-byte as-is (stable git diffs)

Cost scales with the delta, not the corpus. A safety valve aborts if the
re-crawl finds under half the previous pages (a failed crawl, not a real
site change) unless `force` is set.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from .config import STATE_DIRNAME, STATE_FILENAME
from .model import content_hash, utcnow_iso
from .okf import validate_bundle
from .writer import bundle_path_for, prune_empty_dirs, write_bundle_meta, write_concept

_SAFETY_MIN_PAGES = 4
_SAFETY_RATIO = 0.5


def sync_bundle(
    directory: str,
    *,
    max_depth: int | None = None,
    max_pages: int | None = None,
    force: bool = False,
) -> int:
    report = asyncio.run(
        run_sync(directory, max_depth=max_depth, max_pages=max_pages, force=force)
    )
    return 0 if report.get("_ok", True) else 3


async def run_sync(
    directory: str,
    *,
    max_depth: int | None = None,
    max_pages: int | None = None,
    force: bool = False,
    post_sync=(),
) -> dict:
    """Perform the sync; returns the report dict (with a private `_ok` flag).

    `post_sync` is a sequence of `async hook(bundle_dir, report)` callables —
    the extension point calknowledge uses to re-run enrichment/embeddings.
    """
    bundle_dir = Path(directory)
    state_file = bundle_dir / STATE_DIRNAME / STATE_FILENAME
    if not state_file.exists():
        raise SystemExit(f"{directory} is not an okf-kit bundle (no {STATE_DIRNAME}/state.json)")
    state = json.loads(state_file.read_text(encoding="utf8"))
    root_url = state["root_url"]
    config = dict(state.get("config", {}))
    depth = max_depth if max_depth is not None else config.get("max_depth", 3)
    pages_cap = max_pages if max_pages is not None else config.get("max_pages", 200)
    js = config.get("fetcher") == "browser"

    from .crawl import crawl_site, make_fetcher

    print(f"okf sync: re-crawling {root_url}")
    fetcher = make_fetcher(js, respect_robots=config.get("respect_robots", True))
    try:
        crawled = await crawl_site(root_url, fetcher=fetcher, max_depth=depth, max_pages=pages_cap)
    finally:
        await fetcher.close()

    new_pages = {}
    for page in crawled:
        path = bundle_path_for(page.url)
        if path not in new_pages:
            new_pages[path] = page
    new_hash = {path: content_hash(p.markdown) for path, p in new_pages.items()}
    old_hash = {e["path"]: e["hash"] for e in state.get("pages", [])}

    added = sorted(set(new_pages) - set(old_hash))
    removed = sorted(set(old_hash) - set(new_pages))
    changed = sorted(p for p in set(new_pages) & set(old_hash) if new_hash[p] != old_hash[p])

    if (
        not force
        and len(old_hash) > _SAFETY_MIN_PAGES
        and len(new_pages) < len(old_hash) * _SAFETY_RATIO
    ):
        raise SystemExit(
            f"Sync aborted: re-crawl found {len(new_pages)} pages but the bundle has "
            f"{len(old_hash)} — this looks like a failed crawl, not a site change. "
            f"Re-run with --force to apply anyway."
        )

    print(f"Sync diff: {len(added)} added, {len(changed)} changed, {len(removed)} removed")

    ts = utcnow_iso()
    for path in removed:
        (bundle_dir / path).unlink(missing_ok=True)
    prune_empty_dirs(bundle_dir / "pages")
    for path in added + changed:
        write_concept(bundle_dir, new_pages[path], ts)

    from .model import PageRecord

    records = [
        PageRecord(path=path, url=new_pages[path].url, title=new_pages[path].title,
                   content_hash=new_hash[path])
        for path in sorted(new_pages)
    ]
    report = {
        "synced_at": utcnow_iso(),
        "added": len(added),
        "changed": len(changed),
        "removed": len(removed),
        "pages": len(new_pages),
    }
    write_bundle_meta(
        bundle_dir,
        records,
        root_url=root_url,
        config=config,
        log_lines=[f"Sync: +{len(added)} added, ~{len(changed)} changed, -{len(removed)} removed."],
        last_sync=report,
    )

    for hook in post_sync:
        await hook(bundle_dir, report)

    ok = validate_bundle(bundle_dir, quiet=True)
    report["_ok"] = ok
    print(
        f"Sync done: +{len(added)} ~{len(changed)} -{len(removed)} "
        f"({len(new_pages)} pages)" + ("" if ok else "  [BUNDLE INVALID]")
    )
    return report
