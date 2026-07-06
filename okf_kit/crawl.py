"""Crawl a site into an OKF bundle (`okf build`).

`crawl_site` runs the level-by-level BFS and returns the deduped pages;
`build_bundle` writes them. Both `build` and `sync` reuse `crawl_site`.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse

from .mapper import normalize_url
from .model import Page, utcnow_iso
from .okf import validate_bundle
from .writer import bundle_path_for, compute_edges, write_bundle_meta, write_concept

_SHORT_PAGE_CHARS = 200
_JS_HINT_RATIO = 0.30


def _default_output(seed: str) -> Path:
    host = urlparse(seed).netloc.replace(":", "_") or "site"
    return Path(f"./{host}-okf")


def make_fetcher(js: bool, *, respect_robots: bool = True, verbose: bool = False):
    if js:
        from .fetch.browser import BrowserFetcher

        return BrowserFetcher(verbose=verbose)
    from .fetch.http import HttpFetcher

    return HttpFetcher(respect_robots=respect_robots, verbose=verbose)


def normalize_prefix(prefix: str) -> str:
    """Ensure a user-supplied path prefix has leading and trailing slashes."""
    p = "/" + prefix.strip().strip("/")
    return p if p == "/" else p + "/"


def scope_prefix_for(url: str) -> str:
    """Derive the crawl scope from a seed/first-page URL: the section it lives
    in. A path that looks like a file scopes to its directory; a path that
    looks like a section (no extension) scopes under itself.

        https://x/                -> /
        https://x/book/           -> /book/   (normalize strips the slash first)
        https://x/stable/book     -> /stable/book/
        https://x/docs/intro.html -> /docs/
    """
    path = urlparse(url).path
    if not path or path == "/":
        return "/"
    last = path.rsplit("/", 1)[-1]
    if "." in last:
        return path.rsplit("/", 1)[0] + "/"
    return path + "/"


def _in_scope(url_path: str, prefix: str) -> bool:
    if prefix == "/":
        return True
    return url_path == prefix[:-1] or url_path.startswith(prefix)


async def crawl_site(
    seed: str,
    *,
    fetcher,
    max_depth: int,
    max_pages: int,
    path_prefix: str | None = None,
    scope: bool = True,
    on_page=None,
) -> tuple[list[Page], str]:
    """BFS over same-host links within the path scope; returns (pages, prefix).

    Scope: `path_prefix` if given (explicit), `/` if `scope=False` (whole host),
    else auto-derived from the seed page's final (post-redirect) URL.
    """
    seed = normalize_url(seed)
    seed_host = urlparse(seed).netloc
    prefix = None if scope and path_prefix is None else (
        "/" if not scope else normalize_prefix(path_prefix)
    )

    pages: list[Page] = []
    seen_urls: set[str] = {seed}
    seen_paths: set[str] = set()
    current = [seed]
    depth = 0

    while current and len(pages) < max_pages and depth <= max_depth:
        batch = current[: max_pages - len(pages)]
        results = await asyncio.gather(*(fetcher.fetch(u) for u in batch))

        next_level: list[str] = []
        for page in results:
            if page is None:
                continue
            # Auto-scope: the first fetched page (the seed, post-redirect) sets it.
            if prefix is None:
                prefix = scope_prefix_for(page.url)
            path = bundle_path_for(page.url)
            if path in seen_paths or not page.markdown.strip():
                continue
            if len(pages) >= max_pages:
                break
            seen_paths.add(path)
            page.depth = depth
            pages.append(page)
            if on_page:
                on_page(page, path)
            if depth < max_depth:
                for link in page.links:
                    norm = normalize_url(link)
                    p = urlparse(norm)
                    if (
                        p.netloc == seed_host
                        and norm not in seen_urls
                        and _in_scope(p.path, prefix)
                    ):
                        seen_urls.add(norm)
                        next_level.append(norm)
        current = next_level
        depth += 1

    return pages, (prefix or "/")


def build_bundle(
    url: str,
    *,
    output: str | None = None,
    max_depth: int = 3,
    max_pages: int = 200,
    js: bool = False,
    respect_robots: bool = True,
    path_prefix: str | None = None,
    all_paths: bool = False,
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
            path_prefix=path_prefix,
            all_paths=all_paths,
            verbose=verbose,
        )
    )


async def _build(
    url, *, output, max_depth, max_pages, js, respect_robots, path_prefix, all_paths, verbose
) -> int:
    seed = normalize_url(url)
    bundle_dir = Path(output) if output else _default_output(seed)
    fetcher = make_fetcher(js, respect_robots=respect_robots, verbose=verbose)

    print(f"okf build: crawling {seed} (depth<={max_depth}, pages<={max_pages}, {fetcher.kind})")

    def on_page(page: Page, path: str) -> None:
        print(f"  ✓ [{page.depth}] {page.url} -> {path}")

    try:
        pages, prefix = await crawl_site(
            seed,
            fetcher=fetcher,
            max_depth=max_depth,
            max_pages=max_pages,
            path_prefix=path_prefix,
            scope=not all_paths,
            on_page=on_page,
        )
    finally:
        await fetcher.close()

    if not pages:
        print("No pages could be crawled — check the URL is reachable.", file=sys.stderr)
        return 1

    if prefix != "/":
        print(f"  (scope: paths under {prefix} — use --all-paths for the whole host)")

    ts = utcnow_iso()
    records = [r for r in (write_concept(bundle_dir, p, ts) for p in pages) if r]
    present = {r.path for r in records}
    write_bundle_meta(
        bundle_dir,
        records,
        root_url=seed,
        config={
            "max_depth": max_depth,
            "max_pages": max_pages,
            "fetcher": fetcher.kind,
            "respect_robots": respect_robots,
            "path_prefix": prefix,
        },
        log_lines=[f"Built from {seed}: {len(records)} pages."],
        edges=compute_edges(pages, present),
    )

    short = sum(1 for p in pages if len(p.markdown) < _SHORT_PAGE_CHARS)
    if not js and short / len(pages) > _JS_HINT_RATIO:
        print(
            f"\nNote: {short}/{len(pages)} pages extracted very little text — this site "
            "looks JavaScript-rendered.\nTry:  pip install 'okf-kit[js]'  and re-run with  --js",
            file=sys.stderr,
        )

    ok = validate_bundle(bundle_dir)
    print(f"\nBundle: {len(records)} pages -> {bundle_dir}")
    return 0 if ok else 3
