"""HttpFetcher — the default, no-browser page fetcher.

httpx + trafilatura (markdown extraction) + selectolax (title / meta / links).
Covers static and server-rendered sites; JavaScript-rendered sites need the
BrowserFetcher (okf-kit[js]). Respects robots.txt by default.
"""

from __future__ import annotations

import asyncio
import urllib.robotparser
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura
from selectolax.parser import HTMLParser

from .. import __version__
from ..mapper import normalize_url
from ..model import Page, clean_markdown

_USER_AGENT = f"okf-kit/{__version__} (+https://github.com/vinodborole/okf-kit)"
_SKIP_TAGS = ("script", "style", "noscript", "svg", "nav", "footer", "header")


class HttpFetcher:
    kind = "http"

    def __init__(
        self,
        *,
        respect_robots: bool = True,
        timeout: float = 20.0,
        concurrency: int = 8,
        verbose: bool = False,
    ):
        self.respect_robots = respect_robots
        self.verbose = verbose
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": _USER_AGENT},
        )
        self._sem = asyncio.Semaphore(concurrency)
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._robots_lock = asyncio.Lock()

    async def fetch(self, url: str) -> Page | None:
        async with self._sem:
            if self.respect_robots and not await self._allowed(url):
                return None
            try:
                resp = await self._client.get(url)
            except httpx.HTTPError:
                return None
            if resp.status_code >= 400:
                return None
            if "html" not in resp.headers.get("content-type", "").lower():
                return None

            html = resp.text
            final_url = normalize_url(str(resp.url))
            markdown = trafilatura.extract(
                html,
                output_format="markdown",
                include_tables=True,
                include_formatting=True,
                fast=True,  # disable the fallback pass that duplicates small pages
            )
            title, description, links = self._parse(html, str(resp.url))
            if not markdown or not markdown.strip():
                markdown = self._fallback(html, title)
            markdown = clean_markdown(markdown or "")
            if not markdown:
                return None
            return Page(
                url=final_url,
                title=title,
                markdown=markdown,
                description=description,
                links=links,
            )

    async def close(self) -> None:
        await self._client.aclose()

    # -- internals --------------------------------------------------------

    async def _allowed(self, url: str) -> bool:
        host = urlparse(url).netloc
        async with self._robots_lock:
            if host not in self._robots:
                self._robots[host] = await self._load_robots(url)
        rp = self._robots[host]
        return rp is None or rp.can_fetch(_USER_AGENT, url)

    async def _load_robots(self, url: str):
        p = urlparse(url)
        robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
        try:
            resp = await self._client.get(robots_url)
            if resp.status_code >= 400:
                return None  # no robots.txt → allow all
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(resp.text.splitlines())
            return rp
        except httpx.HTTPError:
            return None

    @staticmethod
    def _parse(html: str, base_url: str) -> tuple[str | None, str | None, list[str]]:
        tree = HTMLParser(html)
        title = None
        if tree.css_first("title"):
            title = tree.css_first("title").text(strip=True) or None
        description = None
        meta = tree.css_first('meta[name="description"]')
        if meta and meta.attributes.get("content"):
            description = meta.attributes["content"].strip() or None

        links: list[str] = []
        seen: set[str] = set()
        for a in tree.css("a[href]"):
            href = a.attributes.get("href")
            if not href:
                continue
            absolute = urljoin(base_url, href)
            if urlparse(absolute).scheme not in ("http", "https"):
                continue
            norm = normalize_url(absolute)
            if norm not in seen:
                seen.add(norm)
                links.append(norm)
        return title, description, links

    @staticmethod
    def _fallback(html: str, title: str | None) -> str:
        """Last resort when trafilatura yields nothing: strip chrome, keep
        headings + text. Not markdown-rich, but never empty."""
        tree = HTMLParser(html)
        for tag in _SKIP_TAGS:
            for node in tree.css(tag):
                node.decompose()
        root = tree.css_first("main") or tree.css_first("article") or tree.body
        if root is None:
            return ""
        parts: list[str] = []
        if title:
            parts.append(f"# {title}")
        for node in root.css("h1, h2, h3, h4, p, li"):
            text = node.text(strip=True)
            if not text:
                continue
            tag = node.tag
            if tag in ("h1", "h2", "h3", "h4"):
                parts.append(f"{'#' * int(tag[1])} {text}")
            elif tag == "li":
                parts.append(f"- {text}")
            else:
                parts.append(text)
        return "\n\n".join(parts)
