"""Core data types shared across fetchers, the crawler, and the writer."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

_PILCROW = re.compile(r"\s*¶")
_EXTRA_BLANKS = re.compile(r"\n{3,}")


def content_hash(markdown: str) -> str:
    """Stable hash of a page's crawled markdown — the unit sync diffs on.
    Independent of frontmatter (timestamps), so unchanged content stays
    unchanged across rebuilds."""
    return hashlib.sha256(markdown.encode("utf8")).hexdigest()


def clean_markdown(md: str) -> str:
    """Tidy common extraction artifacts: Sphinx/docs heading anchors (¶) and
    runs of blank lines."""
    md = _PILCROW.sub("", md)
    md = _EXTRA_BLANKS.sub("\n\n", md)
    return md.strip()


@dataclass
class Page:
    """A fetched web page, normalized into the shape the bundle writer needs."""

    url: str
    title: str | None
    markdown: str
    description: str | None = None
    # All absolute http(s) links found on the page; the crawler decides which
    # to follow (same-host, within depth).
    links: list[str] = field(default_factory=list)
    depth: int = 0


@dataclass
class PageRecord:
    """A concept written into the bundle, plus the content hash sync needs."""

    path: str  # bundle-relative, e.g. "pages/docs/intro.md"
    url: str
    title: str | None
    content_hash: str  # sha256 of the crawled markdown (not the frontmatter'd file)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
