"""BrowserFetcher — JS-rendered pages via crawl4ai (okf-kit[js] extra).

Thin adapter producing the same Page shape as HttpFetcher. crawl4ai and its
Playwright Chromium are heavy, so this is import-guarded: `okf build --js`
without the extra installed exits with a clear install hint.
"""

from __future__ import annotations

from ..mapper import normalize_url
from ..model import Page, clean_markdown

_INSTALL_HINT = (
    "--js needs the browser extra. Install it with:\n"
    "    pip install 'okf-kit[js]'\n"
    "    python -m playwright install chromium"
)


class BrowserFetcher:
    kind = "browser"

    def __init__(self, *, verbose: bool = False, **_):
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig
        except ImportError as exc:  # noqa: TRY003
            raise SystemExit(_INSTALL_HINT) from exc
        self._AsyncWebCrawler = AsyncWebCrawler
        self._browser_config = BrowserConfig(headless=True, verbose=verbose)
        self._crawler = None

    async def _ensure(self):
        if self._crawler is None:
            self._crawler = self._AsyncWebCrawler(config=self._browser_config)
            await self._crawler.__aenter__()
        return self._crawler

    async def fetch(self, url: str) -> Page | None:
        from crawl4ai import CrawlerRunConfig

        crawler = await self._ensure()
        result = await crawler.arun(url, config=CrawlerRunConfig())
        if not getattr(result, "success", False):
            return None
        markdown = getattr(result.markdown, "raw_markdown", None) or str(result.markdown or "")
        if not markdown.strip():
            return None
        meta = result.metadata or {}
        links = [
            normalize_url(link["href"])
            for link in (result.links or {}).get("internal", [])
            if link.get("href")
        ]
        return Page(
            url=normalize_url(result.url),
            title=meta.get("title"),
            markdown=clean_markdown(markdown),
            description=meta.get("description"),
            links=links,
        )

    async def close(self) -> None:
        if self._crawler is not None:
            await self._crawler.__aexit__(None, None, None)
