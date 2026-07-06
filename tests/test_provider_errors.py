"""Friendly provider-error messages and Ollama model auto-detection."""

from __future__ import annotations

from okf_kit.chat.providers import _detect_ollama_model, describe_provider_error


# Class names mirror the real openai/httpx SDK exception types.
class NotFoundError(Exception):
    pass


class APIConnectionError(Exception):
    pass


class AuthenticationError(Exception):
    pass


def test_model_not_found_ollama():
    msg = describe_provider_error(NotFoundError("model 'llama3.1' not found"), "ollama", "llama3.1")
    assert "ollama pull llama3.1" in msg
    assert "ollama list" in msg


def test_model_not_found_openai_wording():
    # OpenAI's real 404 says "does not exist", not "not found".
    msg = describe_provider_error(NotFoundError("The model `x` does not exist"), "openai", "x")
    assert "--model" in msg and "openai" in msg


def test_connection_error_ollama():
    msg = describe_provider_error(APIConnectionError("Connection refused"), "ollama", "llama3.1")
    assert "ollama serve" in msg


def test_auth_error():
    msg = describe_provider_error(AuthenticationError("401 unauthorized"), "openai", "gpt-4o-mini")
    assert "Authentication failed" in msg
    assert "API key" in msg


def test_detect_ollama_model_falls_back_when_unreachable():
    # Nothing listening on this port → detection must fall back, not raise.
    assert _detect_ollama_model("http://127.0.0.1:1/v1", "llama3.1") == "llama3.1"
