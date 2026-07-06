# Changelog

All notable changes to okf-kit are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

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

[0.1.1]: https://github.com/vinodborole/okf-kit/releases/tag/v0.1.1
[0.1.0]: https://github.com/vinodborole/okf-kit/releases/tag/v0.1.0
