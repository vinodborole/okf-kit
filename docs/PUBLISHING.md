# Publishing a bundle to the registry

The community registry, **[awesome-okf-kit](https://github.com/vinodborole/awesome-okf-kit)**,
is an index of published OKF bundles. Bundles live in their own repos and ship
as release zips; the registry just points at them.

> **Publish only content you may redistribute** — your own site, or content
> under a permissive license (CC-BY, CC-BY-SA, open-source project docs, public
> domain). `license` and `source_url` are required in your registry entry.

## 1. Build and publish the bundle

```bash
okf build https://your-docs.example.com -o your-docs-okf
okf validate your-docs-okf        # must be CONFORMANT
okf zip your-docs-okf             # -> your-docs-okf.zip
```

Create a repo for the bundle (or use the bundle template), commit it, and
attach `your-docs-okf.zip` to a GitHub Release.

## 2. Keep it fresh automatically

Add a weekly self-sync GitHub Action to the bundle repo:

```yaml
name: sync
on:
  schedule: [{cron: "0 6 * * 1"}]   # Mondays 06:00 UTC
  workflow_dispatch:
jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install okf-kit
      - run: okf sync your-docs-okf
      - name: Commit the delta
        run: |
          git config user.name okf-bot
          git config user.email okf-bot@users.noreply.github.com
          git add -A && git commit -m "sync: $(date -u +%F)" || echo "no changes"
          git push
```

Because sync only rewrites changed pages, these are small commits — the repo
history becomes a record of how the site's knowledge evolved.

## 3. Add it to the registry

Open a PR to `awesome-okf-kit` adding an entry to `registry.yaml`:

```yaml
- name: your-docs
  source_url: https://your-docs.example.com
  description: One line about the docs.
  license: CC-BY-4.0
  publisher: github.com/you
  repo: https://github.com/you/your-docs-okf
  download: https://github.com/you/your-docs-okf/releases/latest/download/your-docs-okf.zip
  okf_version: "0.1"
  pages: 128
  tags: [docs, your-topic]
```

CI validates the schema and runs `okf validate` on the downloaded zip; a
maintainer reviews licensing. Once merged, anyone can:

```bash
okf get your-docs
okf chat your-docs --provider ollama
```
