"""LLM provider abstraction for chat — deliberately tiny (no LangChain).

One protocol, two implementations:
  OpenAICompatProvider  — any OpenAI-compatible endpoint (OpenAI, Ollama,
                          vLLM, LM Studio, OpenRouter). okf-kit[chat].
  AnthropicProvider     — Claude with tool use. okf-kit[anthropic].

`make_provider` returns None when no provider/key is available, so the caller
falls back to zero-key retrieval.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import httpx

# Preset endpoints for OpenAI-compatible servers.
_PRESETS = {
    "openai": {"base_url": None, "key_env": "OPENAI_API_KEY", "default_model": "gpt-4o-mini"},
    "ollama": {"base_url": "http://localhost:11434/v1", "key_env": None, "default_model": "llama3.1"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "key_env": "OPENROUTER_API_KEY",
                   "default_model": "openai/gpt-4o-mini"},
}


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Turn:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


class OpenAICompatProvider:
    def __init__(self, model: str, base_url: str | None, api_key: str):
        try:
            from openai import OpenAI
        except ImportError as exc:  # noqa: TRY003
            raise SystemExit("Chat needs the chat extra:  pip install 'okf-kit[chat]'") from exc
        self.model = model
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    def complete(self, messages: list[dict], tools: list[dict]) -> Turn:
        resp = self._client.chat.completions.create(
            model=self.model, messages=messages, tools=tools or None
        )
        msg = resp.choices[0].message
        calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments=_loads(tc.function.arguments))
            for tc in (msg.tool_calls or [])
        ]
        return Turn(text=msg.content, tool_calls=calls)

    def assistant_message(self, turn: Turn) -> dict:
        m: dict = {"role": "assistant", "content": turn.text or ""}
        if turn.tool_calls:
            m["tool_calls"] = [
                {"id": c.id, "type": "function",
                 "function": {"name": c.name, "arguments": _dumps(c.arguments)}}
                for c in turn.tool_calls
            ]
        return m

    @staticmethod
    def tool_result_message(call: ToolCall, content: str) -> dict:
        return {"role": "tool", "tool_call_id": call.id, "content": content}


class AnthropicProvider:
    def __init__(self, model: str, api_key: str):
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # noqa: TRY003
            raise SystemExit("Claude chat needs:  pip install 'okf-kit[anthropic]'") from exc
        self.model = model
        self._client = Anthropic(api_key=api_key)
        self._system = None

    def complete(self, messages: list[dict], tools: list[dict]) -> Turn:
        system, msgs = _split_system(messages)
        atools = [
            {"name": t["function"]["name"], "description": t["function"]["description"],
             "input_schema": t["function"]["parameters"]}
            for t in tools
        ]
        resp = self._client.messages.create(
            model=self.model, max_tokens=2048, system=system or "", messages=msgs, tools=atools or []
        )
        text_parts, calls = [], []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                calls.append(ToolCall(id=block.id, name=block.name, arguments=dict(block.input)))
        return Turn(text="".join(text_parts) or None, tool_calls=calls)

    def assistant_message(self, turn: Turn) -> dict:
        content: list[dict] = []
        if turn.text:
            content.append({"type": "text", "text": turn.text})
        for c in turn.tool_calls:
            content.append({"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments})
        return {"role": "assistant", "content": content}

    @staticmethod
    def tool_result_message(call: ToolCall, content: str) -> dict:
        return {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": call.id, "content": content}]}


def make_provider(provider: str | None, model: str | None, base_url: str | None):
    """Return a provider instance, or None to use the zero-key retrieval fallback."""
    if provider in (None, "none"):
        return None
    if provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            return None
        return AnthropicProvider(model or "claude-sonnet-5", key)
    if provider in _PRESETS or provider == "custom":
        preset = _PRESETS.get(provider, {})
        url = base_url or preset.get("base_url")
        key_env = preset.get("key_env")
        key = os.environ.get(key_env) if key_env else None
        model = model or preset.get("default_model", "gpt-4o-mini")
        if provider == "ollama":
            key = key or "ollama"  # Ollama ignores the key but the SDK requires one
            if not base_url:  # user didn't force a model — use one Ollama actually has
                model = _detect_ollama_model(url, model)
        if not key:
            return None
        return OpenAICompatProvider(model, url, key)
    raise SystemExit(f"Unknown provider '{provider}'. Use openai/ollama/openrouter/anthropic/custom.")


def _detect_ollama_model(base_url: str, fallback: str) -> str:
    """Pick a model Ollama actually has installed; fall back to the preset."""
    try:
        tags_url = base_url.rsplit("/v1", 1)[0] + "/api/tags"
        models = httpx.get(tags_url, timeout=2.0).json().get("models", [])
        names = [m.get("name", "") for m in models if m.get("name")]
        # Prefer the preset default if it's present, else the first installed model.
        if fallback in names or any(n.split(":")[0] == fallback for n in names):
            return fallback
        return names[0] if names else fallback
    except Exception:  # noqa: BLE001 — Ollama not running/reachable; error surfaces on use
        return fallback


def describe_provider_error(exc: Exception, provider: str | None, model: str | None) -> str:
    """Turn a raw provider/SDK exception into an actionable one-liner."""
    name = type(exc).__name__
    low = str(exc).lower()
    is_ollama = provider == "ollama"

    if "NotFound" in name or "not found" in low or "does not exist" in low or "404" in low:
        if is_ollama:
            return (
                f"Ollama doesn't have the model '{model}'. Install it:\n"
                f"    ollama pull {model}\n"
                f"or pick one you have:  ollama list  →  --model <name>"
            )
        return f"Model '{model}' not found for provider '{provider}' — check --model."
    if "Conn" in name or "connect" in low or "refused" in low:
        if is_ollama:
            return "Can't reach Ollama at localhost:11434 — is it running?  Start it:  ollama serve"
        return f"Can't reach the '{provider}' endpoint — check your network or --base-url."
    if "Auth" in name or "401" in low or "api key" in low or "unauthorized" in low:
        return f"Authentication failed for '{provider}' — check the API key environment variable."
    return f"{provider or 'provider'} error: {exc}"


def _loads(s):
    import json

    try:
        return json.loads(s or "{}")
    except json.JSONDecodeError:
        return {}


def _dumps(d):
    import json

    return json.dumps(d)


def _split_system(messages):
    system = None
    msgs = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            msgs.append(m)
    return system, msgs
