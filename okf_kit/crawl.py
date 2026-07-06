"""Crawl a site into an OKF bundle (`okf build`).

Level-by-level BFS: fetch a depth level concurrently, write concepts, collect
same-host links for the next level, stop at max_depth / max_pages. Produces
the bundle directly (pages + directory indexes + state) and validates it.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse

from .mapper import normalize_url
from .model import utcnow_iso
from .okf import validate_bundle
from .writer import BundleWriter

_SHORT_PAGE_CHARS = 200
_JS_HINT_RATIO = 0.30


def _default_output(seed: str) -> Path:
    host = urlparse(seed).netloc.replace(":", "_") or "site"
    return Path(f"./{host}-okf")


def build_bundle(
    url: str,
    *,
    output: str | None = None,
    max_depth: int = 3,
    max_pages: int = 200,
    js: bool = False,
    respect_robots: bool = True,
    verbose: bool = False,
) -> int:
    return asyncio.run(
        _build(
            url,
            output=output,
            max_depth=max_depth,
            max_pages=max_pages,
            js=js,
            respect_robots=respect_robots,
            verbose=verbose,
        )
    )


async def _build(
    url: str,
    *,
    output: str | None,
    max_depth: int,
    max_pages: int,
    js: bool,
    respect_robots: bool,
    verbose: bool,
) -> int:
    seed = normalize_url(url)
    seed_host = urlparse(seed).netloc
    bundle_dir = Path(output) if output else _default_output(seed)

    if js:
        from .fetch.browser import BrowserFetcher

        fetcher = BrowserFetcher(verbose=verbose)
    else:
        from .fetch.http import HttpFetcher

        fetcher = HttpFetcher(respect_robots=respect_robots, verbose=verbose)

    writer = BundleWriter(bundle_dir)
    timestamp = utcnow_iso()
    short_pages = 0

    print(f"okf build: crawling {seed} (depth<={max_depth}, pages<={max_pages}, {fetcher.kind})")

    seen: set[str] = {seed}
    current = [seed]
    depth = 0
    try:
        while current and len(writer.records) < max_pages and depth <= max_depth:
            budget = max_pages - len(writer.records)
            batch = current[:budget]
            pages = await asyncio.gather(*(fetcher.fetch(u) for u in batch))

            next_level: list[str] = []
            for page in pages:
                if page is None:
                    continue
                if len(writer.records) >= max_pages:
                    break
                record = writer.write_page(page, timestamp)
                if record is None:
                    continue
                if len(page.markdown) < _SHORT_PAGE_CHARS:
                    short_pages += 1
                print(f"  ✓ [{depth}] {page.url} -> {record.path}")
                if depth < max_depth:
                    for link in page.links:
                        norm = normalize_url(link)
                        if urlparse(norm).netloc == seed_host and norm not in seen:
                            seen.add(norm)
                            next_level.append(norm)
            current = next_level
            depth += 1
    finally:
        await fetcher.close()

    if not writer.records:
        print("No pages could be crawled — check the URL is reachable.", file=sys.stderr)
        return 1

    writer.finalize(
        root_url=seed,
        config={
            "max_depth": max_depth,
            "max_pages": max_pages,
            "fetcher": fetcher.kind,
            "respect_robots": respect_robots,
        },
    )

    if not js and short_pages / len(writer.records) > _JS_HINT_RATIO:
        print(
            f"\nNote: {short_pages}/{len(writer.records)} pages extracted very little "
            "text — this site looks JavaScript-rendered.\n"
            "Try:  pip install 'okf-kit[js]'  and re-run with  --js",
            file=sys.stderr,
        )

    ok = validate_bundle(bundle_dir)
    print(f"\nBundle: {len(writer.records)} pages -> {bundle_dir}")
    return 0 if ok else 3
