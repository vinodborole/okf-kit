# okf-kit

**Turn any website into a portable, agent-ready knowledge bundle — no LLM required to start.**

`okf-kit` crawls a site into a
[Google Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
bundle: a directory of markdown concept files with YAML frontmatter and
per-directory `index.md` listings that any agent can navigate with plain file
reads. Build it, keep it in sync as the site changes, publish it, and chat with
it — locally, with your own key, or fully offline via Ollama.

```bash
pip install okf-kit
okf build https://docs.example.com -o docs-okf   # crawl → OKF bundle (no key, no browser)
okf chat docs-okf --provider ollama              # chat offline, no key
```

Or zero-install with [`uv`](https://docs.astral.sh/uv/):

```bash
uvx --from okf-kit okf build https://docs.example.com -o docs-okf
```

Part of the **[calknowledge](https://github.com/vinodborole/calknowledge)**
ecosystem — okf-kit is the lightweight, open library; calknowledge is the full
platform (LLM enrichment, RAG export, retrieval evals, GUI) built on top of it.

---

## Why

Everyone re-crawls and re-indexes the same docs privately and badly. okf-kit
makes a website's knowledge a **portable artifact**:

- **Agents can read an OKF bundle; they can't read your website.** The bundle is
  navigable markdown — no scraping, no SDK, no runtime.
- **Faithful markdown, not text soup.** Real extraction (headings, code, tables),
  boilerplate filtered, JS-rendered when needed.
- **Self-maintaining.** `okf sync` updates only what changed, so a published
  bundle in git produces small delta commits and never goes stale.
- **Works with any LLM, or none.** Chat via OpenAI, Ollama, vLLM, OpenRouter, or
  Claude — or get a zero-key retrieval answer with citations.

## Install

```bash
pip install okf-kit                 # core: build / sync / validate / zip / list / get / visualize
pip install "okf-kit[chat]"         # okf chat via OpenAI-compatible providers (OpenAI, Ollama, …)
pip install "okf-kit[anthropic]"    # Claude as a chat provider
pip install "okf-kit[js]"           # crawl JavaScript-rendered sites (pulls a Playwright Chromium)
pip install "okf-kit[mcp]"          # serve bundles to Claude Code / Cursor over MCP
pip install "okf-kit[enrich]"       # okf build --enrich (LLM descriptions + tags)
```

The default install has **no browser and no LLM SDK** — it installs in seconds.

> **Tip:** install into a dedicated virtualenv so okf-kit's dependencies don't
> mix with your other projects:
> ```bash
> python3 -m venv ~/okf && ~/okf/bin/pip install okf-kit
> ```

### Known limitations

- **`[js]` extra dependency conflict** ([#6](https://github.com/vinodborole/okf-kit/issues/6)):
  `pip install "okf-kit[js]"` currently fails to resolve because core's
  `trafilatura` (2.x) requires `lxml>=6.1.1` while `crawl4ai` pins
  `lxml~=5.3`. Until this is fixed in 0.1.1, install the `[js]` extra in its
  **own** environment, separate from anything that pins an older `lxml`. Core
  okf-kit (the default install, no browser) is unaffected.

## Commands

### Build

```bash
okf build https://docs.example.com -o docs-okf --max-depth 3 --max-pages 200
```

Domain-restricted BFS crawl → an OKF bundle: `pages/` mirror with frontmatter
concepts, a `.okf-kit/state.json` for sync, and an `index.md` in every directory
for agent navigation. Validated on exit. No API key needed. Flags: `--js`
(JS-rendered sites), `--no-robots`, `--enrich` (add LLM descriptions/tags — needs
`[enrich]` + `OPENAI_API_KEY`). If a site looks JavaScript-rendered, build tells
you to re-run with `--js`.

### Sync

```bash
okf sync docs-okf
```

Re-crawls the same site and updates **only the delta** — added pages written,
changed pages rewritten, removed pages deleted, unchanged pages left
byte-for-byte (stable git diffs). A safety valve aborts on a suspiciously empty
re-crawl (`--force` overrides).

### Chat

```bash
okf chat docs-okf --provider ollama                 # offline, no key
okf chat docs-okf --provider openai --trace         # any provider, with citations + a navigation trace
okf chat docs-okf                                   # no provider → zero-key retrieval answer
okf chat docs-okf --resume                          # continue the last session (history is local)
```

The agent navigates the bundle (`list_directory` / `read_concept`) to the most
specific concept and answers **only from what it read**, citing the paths.

| `--provider` | Endpoint | Key |
|---|---|---|
| `openai` | OpenAI | `OPENAI_API_KEY` |
| `ollama` | `localhost:11434` (local) | none |
| `openrouter` | OpenRouter | `OPENROUTER_API_KEY` |
| `anthropic` | Claude | `ANTHROPIC_API_KEY` |
| `custom` | `--base-url` | as configured |

Chat history is stored locally at `~/.okf/chats/<bundle>/`.

### Visualize

```bash
okf visualize docs-okf          # -> docs-okf/graph.html
```

A self-contained interactive graph (nodes = concepts, edges = internal links);
no backend, no CDN — open the HTML from `file://`.

### Serve over MCP

```bash
okf serve-mcp docs-okf          # or --all for every downloaded bundle
```

Exposes `list_bundles` / `list_directory` / `read_concept` / `search_bundle` over
stdio MCP for Claude Code/Desktop, Cursor, and any MCP client.

### Registry

```bash
okf list --remote               # browse published bundles
okf get backstage-docs          # download, validate, install to ~/.okf/bundles/
okf list                        # your local bundles
```

### Package for hand-off

```bash
okf zip docs-okf                # -> docs-okf.zip, ready to publish or share
```

## Publishing

See [docs/PUBLISHING.md](docs/PUBLISHING.md) — build a bundle, ship it as a
release zip with a weekly self-sync Action, and add it to the
[awesome-okf-kit](https://github.com/vinodborole/awesome-okf-kit) registry.
Publish only content you may redistribute.

## Bundle layout

```
docs-okf/
    index.md                 root directory listing (reserved, no frontmatter)
    log.md                   build/sync history
    pages/                   one concept per page (frontmatter + body + citations)
        index.md             directory listing (every directory has one)
        home.md
        docs/…
    .okf-kit/state.json      crawl config, per-page content hashes, link edges
```

## Development

`pip install -e ".[dev]"`, then `pytest -q` (37 tests, fully offline) and
`ruff check okf_kit tests`. See [CONTRIBUTING.md](CONTRIBUTING.md) and the
[CHANGELOG](CHANGELOG.md).

## License

Apache-2.0.
