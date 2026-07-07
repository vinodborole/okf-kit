"""Content-link extraction: graph edges use in-content references only, not the
shared nav/header/footer chrome that appears on every page."""

from __future__ import annotations

from okf_kit.fetch.http import HttpFetcher

_HTML = """<html><head><title>T</title></head><body>
  <nav><a href="/side-a.html">A</a><a href="/side-b.html">B</a></nav>
  <header><a href="/logo.html">home</a></header>
  <main>
    <p>See <a href="/real-ref.html">the reference</a> and
       <a href="/guide.html">the guide</a>.</p>
    <nav class="pagination"><a href="/next.html">next</a></nav>
  </main>
  <footer><a href="/privacy.html">privacy</a></footer>
</body></html>"""


def test_crawl_links_include_everything():
    # discovery must still see nav/footer links, or pages become unreachable
    _, _, links, _ = HttpFetcher._parse(_HTML, "https://x.com/page.html")
    assert any("side-a" in ln for ln in links)
    assert any("privacy" in ln for ln in links)
    assert any("real-ref" in ln for ln in links)


def test_content_links_exclude_chrome():
    _, _, _, clinks = HttpFetcher._parse(_HTML, "https://x.com/page.html")
    assert any("real-ref" in ln for ln in clinks)
    assert any("guide" in ln for ln in clinks)
    assert not any("side-a" in ln for ln in clinks)     # sidebar nav
    assert not any("logo" in ln for ln in clinks)       # header
    assert not any("privacy" in ln for ln in clinks)    # footer
    assert not any("next.html" in ln for ln in clinks)  # in-content pagination nav


def test_content_links_fall_back_to_body_without_main():
    html = '<html><body><nav><a href="/n.html">n</a></nav><p><a href="/c.html">c</a></p></body></html>'
    _, _, _, clinks = HttpFetcher._parse(html, "https://x.com/p")
    assert any("c.html" in ln for ln in clinks)
    assert not any("n.html" in ln for ln in clinks)
