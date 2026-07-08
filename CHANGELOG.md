# Changelog

All notable changes to okf-kit are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

## 0.3.0 — 2026-07-08

### Added
- **`okf serve` — a local HTTP API for GUIs** (new `okf-kit[serve]` extra:
  FastAPI + uvicorn + keyring). Wraps registry / read / chat / settings so a
  desktop app or any web UI can be pure UI over an API, with no duplicated logic.
  Loopback-only, guarded by a per-launch bearer token; prints a machine-readable
  `{"event":"ready","url":…,"token":…}` line for a host shell and can exit with
  its parent (`--parent-pid`). Endpoints: registry, books (list/get/install SSE/
  remove), read (`toc`, `concept` with heading anchors + prev/next), chat
  (sessions + `ask` SSE that streams tokens then cited sources), and settings
  (API key stored in the OS keychain via keyring, never returned). Consume-only —
  it does **not** pull the crawl stack, so it stays light to bundle in an app.
- **Deep-linkable chat citations.** Chat sources now resolve to
  `{concept_id, title, section, anchor, snippet}` (over the API) so a UI can jump
  from a citation straight to that section in the reader.

### Changed
- `make_provider(...)` accepts an optional `api_key` (used by `okf serve` to pass
  a keychain-stored key); it still falls back to the provider's env var.

## 0.2.0 — 2026-07-07

### Changed
- **`okf visualize` is now a readable explorer that works on *any* OKF bundle.**
  Replaced the force-directed graph (a hairball on densely-linked docs) with a
  collapsible **tree explorer** of the bundle's concepts, plus a detail pane
  showing each concept's frontmatter, rendered markdown body, the concepts it
  **links to**, and the concepts that **cite it** (backlinks). Output is
  `viz.html`. Self-contained, no CDN.
- **General OKF consumer.** A new `bundle_reader` reads concepts and derives
  edges from concept-to-concept markdown links in the bodies (the spec's link
  graph), so `visualize` works on bundles produced by any tool — verified on
  Google's `reference-agent` sample bundles (ga4, stackoverflow, crypto). It
  still uses okf-kit's recorded `state.json` edges when present.

### Fixed
- **Graph/detail edges ignore navigation chrome.** Link extraction now keeps a
  content-only link set (from `<main>`/`<article>`, minus `nav`/`header`/
  `footer`/`aside`), used for edges — so they're real references, not the shared
  sidebar on every page. On the Backstage docs this cut edges from 6,977 to 550.
  Crawling still uses all links so pages stay discoverable.

## 0.1.8 — 2026-07-06

### Fixed
- **`okf visualize` graph no longer spins out of control.** The force layout
  had no cooling — it re-applied full-strength forces every frame forever, so
  with many nodes it jittered/drifted endlessly instead of settling. It now
  anneals (an `alpha` that decays to zero and then freezes the layout), caps
  the repulsion force so overlapping nodes don't fling apart, and damps
  velocity harder. Dragging briefly reheats it, then it re-settles. Verified
  numerically: post-settle movement drops from ~1935 to 0.

## 0.1.7 — 2026-07-06

### Fixed
- **Redirect/nav stubs no longer dead-end a crawl.** Seeding a URL that's a
  content-less `<meta http-equiv="refresh">` stub (e.g. `https://backstage.io/docs/`,
  which bounces to a first page) previously yielded `No pages could be crawled`.
  okf-kit now follows meta-refresh targets and extracts a page's links even
  when the page itself has no body text — so the crawl reaches the real
  content, scoped to the seed's section. Empty stubs are still never written
  as concepts.

## 0.1.6 — 2026-07-06

### Fixed
- **`okf serve-mcp` no longer corrupts the MCP stream.** The startup banner was
  printed to stdout, which is the JSON-RPC channel in a stdio MCP server, so
  clients logged `Failed to parse JSONRPC message`. The banner now goes to
  stderr; stdout carries only protocol messages.

### Changed
- Added a test that spawns the server and asserts the banner stays off stdout.

## 0.1.5 — 2026-07-06

### Fixed
- **`okf visualize` graph now renders.** The generated `graph.html` was blank:
  the animation `loop()` started before `hover`/`drag` were declared, so the
  first frame threw a temporal-dead-zone `ReferenceError` and the canvas never
  drew. Declared the interaction state before the loop.

### Changed
- Visualize tests now **execute the generated page's JavaScript** headless
  (Node DOM/canvas stubs) so a runtime error in the graph fails the suite —
  plus a structural guard that interaction state is declared before the loop.

## 0.1.4 — 2026-07-06

### Fixed
- **Clean installs work again.** `pip install okf-kit` in a fresh environment
  failed at `import trafilatura` with `lxml.html.clean module is now a separate
  project`, because modern `lxml` (>=5.2) split that module into the
  `lxml-html-clean` package, which trafilatura's `justext` dependency needs.
  It's now a direct dependency. (Environments that already had it — including
  the maintainer's and the previous CI — masked the bug.)

### Changed
- CI adds a **clean-install job**: it installs the built wheel into an isolated
  venv with no dev/test extras and imports the crawl path, so a missing runtime
  dependency fails CI the way it would for a real user.

## 0.1.3 — 2026-07-06

### Added
- **Path-scoped crawling.** `okf build` now scopes the crawl to the seed's
  path section by default (auto-derived from the seed's final, post-redirect
  URL), so `okf build https://doc.rust-lang.org/book/` stays under `/book/`
  instead of wandering into the rest of the host. Override with
  `--path-prefix PATH` or `--all-paths` (whole host). The scope is stored in
  `state.json` and honored by `sync`; pre-0.1.3 bundles default to whole-host.

## 0.1.2 — 2026-07-06

### Fixed
- **`validate` / `zip` / `sync` / `visualize` now accept a downloaded bundle
  name**, not just a directory path — matching `chat` / `get`. Previously
  `okf visualize rust-book` failed with "not an okf-kit bundle" while
  `okf chat rust-book` worked. A local path still works unchanged.

## 0.1.1 — 2026-07-06

### Fixed
- **`[js]` extra now resolves** ([#6](https://github.com/vinodborole/okf-kit/issues/6)):
  the extra constrains `trafilatura` to a build whose `lxml` requirement is
  compatible with `crawl4ai` (`lxml~=5.3`), so `pip install "okf-kit[js]"`
  installs cleanly. Plain installs still get the latest `trafilatura`.
- **Markdown extraction is version-agnostic** — works with `trafilatura` 1.x
  (`no_fallback`) and 2.x (`fast`), detected at import.

### Changed
- **Friendly chat errors.** A provider failure (e.g. Ollama missing the model,
  endpoint unreachable, bad key) now prints an actionable one-line message
  instead of a raw traceback, and the REPL keeps running.
- **Ollama model auto-detection.** With `--provider ollama` and no `--model`,
  okf-kit queries Ollama for an installed model instead of assuming
  `llama3.1`; the resolved model is shown in the chat header.

## 0.1.0 — 2026-07-06

First release — turn any website into a portable, agent-ready
[Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
bundle. No LLM and no browser required to start.

```bash
pip install okf-kit
okf build https://docs.example.com -o docs-okf   # crawl → OKF bundle (no key, no browser)
okf chat docs-okf --provider ollama              # chat offline, no key
```

### Added
- **`okf build`** — domain-restricted crawl → conformant OKF bundle
  (frontmatter concepts + per-directory `index.md` for agent navigation).
  HTTP fetcher by default (httpx + trafilatura); `--js` for
  JavaScript-rendered sites; `--enrich` for optional LLM descriptions/tags.
- **`okf sync`** — incremental re-crawl: updates only added/changed/removed
  pages, leaving unchanged ones byte-for-byte (small git diffs), with a
  safety valve against failed crawls.
- **`okf chat`** — navigation agent that answers from the bundle with
  citations. Any OpenAI-compatible provider (OpenAI, Ollama offline, vLLM,
  OpenRouter) or Claude, plus a zero-key retrieval fallback when no LLM is
  configured. Local chat history (`--resume`, `--history`, `--trace`).
- **`okf visualize`** — self-contained interactive HTML graph (no backend,
  no CDN).
- **`okf serve-mcp`** — expose bundles to Claude Code / Cursor over MCP.
- **`okf list` / `okf get`** — discover and download published bundles from
  the [awesome-okf-kit](https://github.com/vinodborole/awesome-okf-kit)
  registry.
- **`okf validate` / `okf zip`** — OKF v0.1 conformance check and packaging
  for hand-off.

### Notes
- Core install has no browser and no LLM SDK. Extras: `[chat]`,
  `[anthropic]`, `[js]`, `[mcp]`, `[enrich]`.
- 37 tests, fully offline; CI on Python 3.10/3.13 × Ubuntu/macOS.
- Apache-2.0. The lightweight library behind
  [calknowledge](https://github.com/vinodborole/calknowledge).

### Known issues
- The `[js]` extra can't be installed in the same environment as core:
  `trafilatura` 2.x requires `lxml>=6.1.1` while `crawl4ai` pins `lxml~=5.3`.
  Install `[js]` in its own environment for now. Tracked in
  [#6](https://github.com/vinodborole/okf-kit/issues/6), fix planned for 0.1.1.

[0.3.0]: https://github.com/vinodborole/okf-kit/releases/tag/v0.3.0
[0.2.0]: https://github.com/vinodborole/okf-kit/releases/tag/v0.2.0
[0.1.8]: https://github.com/vinodborole/okf-kit/releases/tag/v0.1.8
[0.1.7]: https://github.com/vinodborole/okf-kit/releases/tag/v0.1.7
[0.1.6]: https://github.com/vinodborole/okf-kit/releases/tag/v0.1.6
[0.1.5]: https://github.com/vinodborole/okf-kit/releases/tag/v0.1.5
[0.1.4]: https://github.com/vinodborole/okf-kit/releases/tag/v0.1.4
[0.1.3]: https://github.com/vinodborole/okf-kit/releases/tag/v0.1.3
[0.1.2]: https://github.com/vinodborole/okf-kit/releases/tag/v0.1.2
[0.1.1]: https://github.com/vinodborole/okf-kit/releases/tag/v0.1.1
[0.1.0]: https://github.com/vinodborole/okf-kit/releases/tag/v0.1.0
