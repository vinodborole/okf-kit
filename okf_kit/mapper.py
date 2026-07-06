"""Map crawled URLs to filesystem paths that mirror the site hierarchy.

Ported from calknowledge, unchanged — the URL→path logic is the piece that
was hardened across three production crawls (root → index, trailing-slash
dedup, extension stripping, query-string disambiguation, unsafe-char
sanitizing).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

_PAGE_EXTENSIONS = {".html", ".htm", ".php", ".asp", ".aspx", ".jsp"}
_UNSAFE_CHARS = re.compile(r'[<>:"\\|?*\x00-\x1f]')


def normalize_url(url: str) -> str:
    """Canonical form used for deduplication: no fragment, no trailing slash."""
    p = urlparse(url)
    path = p.path.rstrip("/") or "/"
    normalized = f"{p.scheme}://{p.netloc}{path}"
    if p.query:
        normalized += f"?{p.query}"
    return normalized


def _sanitize_segment(segment: str) -> str:
    segment = _UNSAFE_CHARS.sub("-", segment).strip(". ")
    return segment or "unnamed"


def url_to_relpath(url: str) -> PurePosixPath:
    """Convert a URL into a relative path (without extension).

    https://site.com/               -> index
    https://site.com/getting-started -> getting-started
    https://site.com/api/auth/login  -> api/auth/login
    https://site.com/page?tab=2      -> page-q-<hash>
    """
    p = urlparse(url)
    path = unquote(p.path).strip("/")

    if not path:
        rel = PurePosixPath("index")
    else:
        rel = PurePosixPath(path)
        if rel.suffix.lower() in _PAGE_EXTENSIONS:
            rel = rel.with_suffix("")

    parts = [_sanitize_segment(part) for part in rel.parts]

    if p.query:
        digest = hashlib.sha1(p.query.encode("utf8")).hexdigest()[:8]
        parts[-1] = f"{parts[-1]}-q-{digest}"

    return PurePosixPath(*parts)
