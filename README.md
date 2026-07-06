# okf-kit

**Turn any website into a portable, agent-ready knowledge bundle — no LLM required to start.**

`okf-kit` crawls a site and produces a
[Google Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
bundle: a directory of markdown concept files with YAML frontmatter and
per-directory `index.md` listings that any agent can navigate with plain file
reads. Build it, keep it in sync as the site changes, publish it, and chat
with it — locally, with your own LLM key, or fully offline via Ollama.

```bash
pip install okf-kit
okf build https://docs.example.com -o example-okf   # crawl → OKF bundle (no key needed)
okf validate example-okf                             # OKF v0.1 conformance check
okf zip example-okf                                  # package for hand-off
```

Part of the **[calknowledge](https://github.com/vinodborole/calknowledge)**
ecosystem — okf-kit is the lightweight, open library; calknowledge is the full
platform (LLM enrichment, RAG export, retrieval evals, GUI) built on top of it.

## Status

Early development, built milestone by milestone:

- **M0 — scaffolding** ✅ — package, CLI skeleton, CI, license
- **M1 — build/validate/zip + HTTP fetcher** ✅ — crawl a site into a conformant bundle, no browser
- **M2 — sync** ✅ — incremental re-crawl (add/change/remove only the delta)
- **M3 — consume & talk** ✅ — registry (`list`/`get`), `chat` (any provider, offline via Ollama, zero-key retrieval fallback), `visualize` (interactive HTML graph), `serve-mcp`
- **M4 — polish & release**: docs, PyPI

```bash
okf build https://docs.example.com -o docs-okf   # crawl → bundle (no key)
okf sync docs-okf                                # incremental update
okf chat docs-okf --provider ollama              # chat offline, no key
okf chat docs-okf --provider openai --trace      # or any provider, with citations + trace
okf visualize docs-okf                           # interactive HTML graph
okf serve-mcp docs-okf                           # expose to Claude Code / Cursor via MCP
okf list --remote  &&  okf get <name>            # discover & download published bundles
```

## License

Apache-2.0.
