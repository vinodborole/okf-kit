"""Chat: navigation agent (fake provider), retrieval fallback, history."""

from __future__ import annotations

from okf_kit.chat import agent, retrieval
from okf_kit.chat.history import History
from okf_kit.chat.providers import ToolCall, Turn


class FakeProvider:
    """Scripts a two-step navigation: read one concept, then answer."""

    def __init__(self):
        self._step = 0

    def complete(self, messages, tools):
        self._step += 1
        if self._step == 1:
            return Turn(tool_calls=[ToolCall(id="t1", name="read_concept",
                        arguments={"path": "/pages/docs/guide/install.md"})])
        return Turn(text="Install with `pip install acme-cli` [/pages/docs/guide/install.md].")

    def assistant_message(self, turn):
        return {"role": "assistant", "content": turn.text or "", "_calls": turn.tool_calls}

    def tool_result_message(self, call, content):
        return {"role": "tool", "content": content}


def test_agent_navigates_and_answers(built_bundle):
    result = agent.ask(built_bundle, "How do I install?", FakeProvider())
    assert "pip install acme-cli" in result["answer"]
    assert "/pages/docs/guide/install.md" in result["sources"]
    assert any(s["tool"] == "read_concept" for s in result["steps"])


def test_retrieval_fallback_no_llm(built_bundle):
    result = retrieval.answer(built_bundle, "installation")
    assert "retrieval-only" in result["answer"].lower()
    assert result["sources"]


def test_history_roundtrip(okf_home):
    h = History("acme-docs")
    h.append("user", "hi")
    h.append("assistant", "hello", meta={"sources": ["/x"]})
    loaded = h.load()
    assert [r["role"] for r in loaded] == ["user", "assistant"]
    assert History.latest("acme-docs").path == h.path
    assert History.list_sessions("acme-docs")[0][1] == 1  # one user turn
