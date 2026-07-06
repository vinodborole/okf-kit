"""URL normalization and URL→path mapping."""

from __future__ import annotations

from okf_kit.mapper import normalize_url, url_to_relpath


def test_normalize_strips_fragment_and_trailing_slash():
    assert normalize_url("https://x.com/a/") == "https://x.com/a"
    assert normalize_url("https://x.com/a#frag") == "https://x.com/a"
    assert normalize_url("https://x.com/") == "https://x.com/"
    assert normalize_url("https://x.com/s?q=1") == "https://x.com/s?q=1"


def test_relpath_cases():
    assert str(url_to_relpath("https://x.com/")) == "index"
    assert str(url_to_relpath("https://x.com/getting-started")) == "getting-started"
    assert str(url_to_relpath("https://x.com/api/auth/login")) == "api/auth/login"
    assert str(url_to_relpath("https://x.com/guide/install.html")) == "guide/install"


def test_relpath_query_disambiguated():
    a = str(url_to_relpath("https://x.com/s?tab=1"))
    b = str(url_to_relpath("https://x.com/s?tab=2"))
    assert a != b and a.startswith("s-q-")
