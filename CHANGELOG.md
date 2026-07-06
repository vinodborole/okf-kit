# Changelog

All notable changes to okf-kit are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

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

[0.1.4]: https://github.com/vinodborole/okf-kit/releases/tag/v0.1.4
[0.1.3]: https://github.com/vinodborole/okf-kit/releases/tag/v0.1.3
[0.1.2]: https://github.com/vinodborole/okf-kit/releases/tag/v0.1.2
[0.1.1]: https://github.com/vinodborole/okf-kit/releases/tag/v0.1.1
[0.1.0]: https://github.com/vinodborole/okf-kit/releases/tag/v0.1.0
