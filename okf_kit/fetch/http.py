"""HttpFetcher — the default, no-browser page fetcher.

httpx + trafilatura (markdown extraction) + selectolax (title / meta / links).
Covers static and server-rendered sites; JavaScript-rendered sites need the
BrowserFetcher (okf-kit[js]). Respects robots.txt by default.
"""

from __future__ import annotations

import asyncio
import inspect
import re
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

# Disable trafilatura's fallback pass (it duplicates small pages). The arg is
# `fast` in trafilatura 2.x and `no_fallback` in 1.x — pick whichever this
# install has, so core works with the older 1.x that the [js] extra
# (crawl4ai, lxml~=5.3) needs.
_NO_FALLBACK_KW = (
    "fast" if "fast" in inspect.signature(trafilatura.extract).parameters else "no_fallback"
)


def _extract_markdown(html: str) -> str | None:
    return trafilatura.extract(
        html,
        output_format="markdown",
        include_tables=True,
        include_formatting=True,
        **{_NO_FALLBACK_KW: True},
    )


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
            markdown = _extract_markdown(html)
            title, description, links, content_links = self._parse(html, str(resp.url))
            if not markdown or not markdown.strip():
                markdown = self._fallback(html, title)
            markdown = clean_markdown(markdown or "")
            # Keep a content-less page only if it has links to follow (e.g. a
            # redirect/nav stub) — the crawler uses the links but won't write it.
            if not markdown and not links:
                return None
            return Page(
                url=final_url,
                title=title,
                markdown=markdown,
                description=description,
                links=links,
                content_links=content_links,
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
    def _parse(html: str, base_url: str) -> tuple[str | None, str | None, list[str], list[str]]:
        tree = HTMLParser(html)
        title = None
        if tree.css_first("title"):
            title = tree.css_first("title").text(strip=True) or None
        description = None
        meta = tree.css_first('meta[name="description"]')
        if meta and meta.attributes.get("content"):
            description = meta.attributes["content"].strip() or None

        def hrefs(node) -> list[str]:
            out: list[str] = []
            seen: set[str] = set()
            for a in node.css("a[href]"):
                href = a.attributes.get("href")
                if not href:
                    continue
                absolute = urljoin(base_url, href)
                if urlparse(absolute).scheme not in ("http", "https"):
                    continue
                norm = normalize_url(absolute)
                if norm not in seen:
                    seen.add(norm)
                    out.append(norm)
            return out

        # All links — used by the crawler to discover pages (nav included, since
        # the sidebar is often how you reach every page).
        links = hrefs(tree)

        # A client-side meta-refresh redirect (common on section roots like
        # /docs/ that bounce to a first page) has no <a> — follow its target.
        seen = set(links)
        for m in tree.css("meta"):
            if (m.attributes.get("http-equiv") or "").lower() != "refresh":
                continue
            hit = re.search(r"url\s*=\s*(.+)", m.attributes.get("content") or "", re.I)
            if hit:
                target = normalize_url(urljoin(base_url, hit.group(1).strip().strip("'\"")))
                if urlparse(target).scheme in ("http", "https") and target not in seen:
                    seen.add(target)
                    links.insert(0, target)
            break

        # Content links — the graph/edges use these: from the main content
        # region only, with nav/header/footer/aside chrome removed, so edges are
        # real in-content references, not shared navigation on every page.
        root = tree.css_first("main") or tree.css_first("article") or tree.body
        content_links: list[str] = []
        if root is not None:
            for node in root.css('nav, header, footer, aside, [role="navigation"]'):
                node.decompose()
            content_links = hrefs(root)
        return title, description, links, content_links

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
