"""Optional LLM enrichment for `okf build --enrich` (okf-kit[enrich]).

A thin, opt-in hook: for each concept, add a one-sentence `description` and
topical `tags` to the frontmatter via the OpenAI API. okf-kit's whole point is
that it needs no LLM to be useful — this only runs when you ask for it and a
key is present. (Richer enrichment — typed entities, relationship graphs —
lives in calknowledge.)
"""

from __future__ import annotations

import os

import yaml

from .bundle_nav import _concept_files, _split_frontmatter
from .okf import frontmatter

_SYSTEM = (
    "Summarize a documentation page. Return a single factual sentence describing "
    "the page and 3–7 lowercase topical keywords."
)
_SCHEMA = {
    "name": "page_summary",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "description": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["description", "tags"],
    },
}


def _openai_enricher(model: str):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("--enrich needs OPENAI_API_KEY (and:  pip install 'okf-kit[enrich]').")
    try:
        from openai import OpenAI
    except ImportError as exc:  # noqa: TRY003
        raise SystemExit("--enrich needs:  pip install 'okf-kit[enrich]'") from exc
    client = OpenAI(api_key=key)

    def enrich(title: str | None, body: str) -> dict:
        import json

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"Title: {title}\n\n{body[:6000]}"},
            ],
            response_format={"type": "json_schema", "json_schema": _SCHEMA},
        )
        return json.loads(resp.choices[0].message.content)

    return enrich


def enrich_bundle(bundle_dir, *, model: str = "gpt-4o-mini", enricher=None) -> int:
    """Add description + tags to every concept's frontmatter. Returns the count."""
    enricher = enricher or _openai_enricher(model)
    n = 0
    for md in _concept_files(bundle_dir):
        text = md.read_text(encoding="utf8")
        if not text.startswith("---\n"):
            continue
        end = text.index("\n---\n", 4)
        fm = yaml.safe_load(text[4:end]) or {}
        rest = text[end + 5 :]
        title, body = _split_frontmatter(text)
        try:
            result = enricher(title, body)
        except Exception as exc:  # noqa: BLE001 — one page failing must not kill the run
            print(f"  ✗ {md.name}: {exc}")
            continue
        if result.get("description"):
            fm["description"] = result["description"]
        if result.get("tags"):
            fm["tags"] = result["tags"]
        md.write_text(frontmatter(fm) + rest, encoding="utf8")
        n += 1
    print(f"Enriched {n} concepts with descriptions + tags")
    return n
