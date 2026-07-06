"""Terminal chat loop for `okf chat`."""

from __future__ import annotations

from pathlib import Path

from ..registry import resolve_bundle
from . import agent, retrieval
from .history import History
from .providers import describe_provider_error, make_provider


def run_chat(
    name_or_dir: str,
    *,
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    trace: bool = False,
    resume: bool = False,
    show_history: bool = False,
) -> int:
    bundle_dir = resolve_bundle(name_or_dir)
    bundle_name = Path(bundle_dir).name

    if show_history:
        sessions = History.list_sessions(bundle_name)
        if not sessions:
            print("No saved chats for this bundle.")
        for name, turns in sessions:
            print(f"{name}  ({turns} turns)")
        return 0

    prov = make_provider(provider, model, base_url)
    history = History.latest(bundle_name) if resume else History(bundle_name)
    if resume and history is None:
        history = History(bundle_name)

    if prov is None:
        print("No LLM provider configured — retrieval-only mode.")
        print("For a synthesized answer:  --provider ollama  (offline)  or  --provider openai\n")
    else:
        used_model = getattr(prov, "model", model)
        print(f"Chatting with '{bundle_name}' via {provider} ({used_model}) — Ctrl-D to exit.\n")

    while True:
        try:
            question = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not question:
            continue

        history.append("user", question)
        try:
            result = retrieval.answer(bundle_dir, question) if prov is None else agent.ask(
                bundle_dir, question, prov
            )
        except Exception as exc:  # noqa: BLE001 — a provider error shouldn't crash the REPL
            print("\n" + describe_provider_error(exc, provider, getattr(prov, "model", model)) + "\n")
            continue
        print(f"\n{result['answer']}\n")
        if trace and result["steps"]:
            print("  trace: " + " → ".join(f"{s['tool']} {s['path']}" for s in result["steps"]))
        if result["sources"]:
            print("  sources: " + ", ".join(result["sources"]))
        print()
        history.append("assistant", result["answer"],
                       meta={"steps": result["steps"], "sources": result["sources"]})
