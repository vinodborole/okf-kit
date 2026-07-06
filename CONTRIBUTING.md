# Contributing to okf-kit

Thanks for helping build the open library for portable website knowledge.

## Dev setup

```bash
git clone https://github.com/vinodborole/okf-kit.git
cd okf-kit
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -q          # 37 tests, fully offline (a fixture site is served in-process)
ruff check okf_kit tests
```

Optional extras for the features that use them: `.[chat]` (chat providers),
`.[js]` (JS-rendered crawling), `.[mcp]` (MCP server), `.[enrich]`.

## Guidelines

- **Keep the core lightweight.** New heavy dependencies belong behind an extra,
  not in the default install. The promise is `pip install okf-kit` in seconds.
- **The spec is the contract.** Anything touching the bundle format must keep
  `okf validate` passing; add a test.
- **Tests are offline.** Use the `fixture_site` / `mutable_site` / `built_bundle`
  fixtures — never hit the network in CI. Live smoke tests go behind an env flag.
- **Match the style.** ruff-clean; small, focused functions; docstrings that say
  *why*.

## Pull requests

One logical change per PR, with tests. CI (lint + pytest on 3.10/3.13 ×
ubuntu/macOS) must be green. See `docs/` in the
[calknowledge](https://github.com/vinodborole/calknowledge) repo for the
ecosystem roadmap and milestone plan.
