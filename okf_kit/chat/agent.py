"""The bundle-navigation agent: answer a question by walking the OKF bundle.

Ported from calknowledge's OKF-mode agent (verified to navigate large bundles
correctly with independent LLMs): seed the root index, descend directory
indexes to the most specific concept, answer only from what was read.
"""

from __future__ import annotations

from pathlib import Path

from ..bundle_nav import list_directory, read_concept

MAX_STEPS = 16

SYSTEM = """\
You are a knowledge agent answering questions from an OKF bundle: a directory
of markdown concept files with YAML frontmatter. Every directory has an
index.md listing its contents.

Navigate with the tools:
- list_directory(path): list a directory (e.g. "/", "/pages", "/pages/docs")
- read_concept(path): read a file (e.g. "/pages/docs/intro.md")

Strategy: the root index is provided below. Descend through directory indexes
to the MOST SPECIFIC concept for the question — don't stop at a general page
when a dedicated one exists. If a tool errors, read the nearest parent
index.md. Answer ONLY from concept files you have read; if the bundle doesn't
contain the answer, say so. Cite the bundle paths you used."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List entries in a directory of the OKF bundle.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Bundle path, e.g. /pages"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_concept",
            "description": "Read a markdown concept file from the OKF bundle.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Bundle path, e.g. /index.md"}},
                "required": ["path"],
            },
        },
    },
]


def ask(bundle_dir, question: str, provider, *, max_steps: int = MAX_STEPS) -> dict:
    """Run the navigation loop; returns {answer, steps, sources}."""
    bundle_dir = Path(bundle_dir)
    root_index = read_concept(bundle_dir, "/index.md")
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Question: {question}\n\nBundle root index (/index.md):\n{root_index}"},
    ]
    steps: list[dict] = []
    read_paths: list[str] = []
    answer = None

    for _ in range(max_steps):
        turn = provider.complete(messages, TOOLS)
        messages.append(provider.assistant_message(turn))
        if not turn.tool_calls:
            answer = turn.text
            break
        for call in turn.tool_calls:
            path = call.arguments.get("path", "/")
            if call.name == "read_concept":
                result = read_concept(bundle_dir, path)
                if not result.startswith("error:") and path not in read_paths:
                    read_paths.append(path)
            else:
                result = list_directory(bundle_dir, path)
            steps.append({"tool": call.name, "path": path})
            messages.append(provider.tool_result_message(call, result))

    if answer is None:
        messages.append({"role": "user", "content": "Stop exploring and answer from what you've read."})
        answer = provider.complete(messages, []).text

    return {"answer": answer or "", "steps": steps, "sources": read_paths}
