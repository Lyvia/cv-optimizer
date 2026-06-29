"""
test_llm_client_gemini.py — Automated tests for LLMClient._gemini() against
the google-genai SDK (the SDK migrated to from the deprecated
google-generativeai — see CVO-2 in Linear).

Run with: python -m pytest test_llm_client_gemini.py -v

No real API calls are made: google.genai is replaced with a fake module via
sys.modules before each test (auto-restored by pytest's monkeypatch), shaped
to match the real SDK's actual API as confirmed by local introspection and
https://ai.google.dev/gemini-api/docs/migrate / https://googleapis.github.io/python-genai/:

    from google import genai
    from google.genai import types
    client = genai.Client(api_key=...)
    client.models.generate_content(
        model=..., contents=...,
        config=types.GenerateContentConfig(
            system_instruction=..., max_output_tokens=..., temperature=...,
            thinking_config=types.ThinkingConfig(thinking_budget=...),
        ),
    )

Real google.genai.errors.APIError exposes a structured `.code` (HTTP status,
e.g. 429/403) — the fake error class below mirrors that exact shape.
"""

import sys
import types as pytypes

import pytest

from src.llm_client import LLMClient


class _FakeAPIError(Exception):
    """Mirrors google.genai.errors.APIError's shape: a `.code` (HTTP status)
    and `.message`, which is what LLMClient._gemini_error_code() reads."""

    def __init__(self, code: int, message: str):
        super().__init__(f"{code} {message}")
        self.code = code
        self.message = message


class _FakeThinkingConfig:
    def __init__(self, thinking_budget=None, **_ignored):
        self.thinking_budget = thinking_budget


class _FakeGenerateContentConfig:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FakeResponse:
    def __init__(self, text):
        self.text = text


def _install_fake_genai(monkeypatch, model_behavior: dict, calls: list):
    """model_behavior: dict[model_name] -> response text (str) or an
    Exception instance to raise. calls: list that records (model, config)
    for every generate_content call, for assertions on what was sent."""

    class _FakeModels:
        def generate_content(self, *, model, contents, config=None):
            calls.append((model, config))
            behavior = model_behavior.get(model)
            if isinstance(behavior, Exception):
                raise behavior
            return _FakeResponse(behavior)

    class _FakeClient:
        def __init__(self, api_key=None):
            self.api_key = api_key
            self.models = _FakeModels()

    fake_types = pytypes.SimpleNamespace(
        GenerateContentConfig=_FakeGenerateContentConfig,
        ThinkingConfig=_FakeThinkingConfig,
    )
    fake_genai = pytypes.SimpleNamespace(Client=_FakeClient, types=fake_types)

    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)


def _client(model="gemini-2.5-flash") -> LLMClient:
    return LLMClient(provider="Google (Gemini)", api_key="fake-key", model=model)


# ─── Successful generation ──────────────────────────────────────────────────

def test_successful_generation_returns_text(monkeypatch):
    calls = []
    _install_fake_genai(monkeypatch, {"gemini-2.5-flash": "Hello from Gemini!"}, calls)

    result = _client().generate(system="sys", user="hello", max_tokens=123)

    assert result == "Hello from Gemini!"
    assert len(calls) == 1
    model_used, config = calls[0]
    assert model_used == "gemini-2.5-flash"
    assert config.system_instruction == "sys"
    assert config.max_output_tokens == 123
    assert config.temperature == 0.7


# ─── Thinking budget — the actual root cause of CVO-2 ──────────────────────

def test_thinking_disabled_for_flash(monkeypatch):
    """Flash models must get thinking_budget=0 -- this is the fix for the
    truncated-CV bug (thinking tokens were silently eating max_output_tokens)."""
    calls = []
    _install_fake_genai(monkeypatch, {"gemini-2.5-flash": "ok"}, calls)

    _client("gemini-2.5-flash").generate(system="sys", user="hello", max_tokens=1000)

    _, config = calls[0]
    assert config.thinking_config.thinking_budget == 0


def test_thinking_disabled_for_flash_lite(monkeypatch):
    calls = []
    _install_fake_genai(monkeypatch, {"gemini-2.5-flash-lite": "ok"}, calls)

    _client("gemini-2.5-flash-lite").generate(system="sys", user="hello", max_tokens=1000)

    _, config = calls[0]
    assert config.thinking_config.thinking_budget == 0


def test_thinking_budget_128_for_pro_which_cannot_fully_disable_it(monkeypatch):
    """gemini-2.5-pro requires a minimum non-zero thinking budget (per
    Gemini API docs) -- thinking_budget=0 would be rejected for this model."""
    calls = []
    _install_fake_genai(monkeypatch, {"gemini-2.5-pro": "ok"}, calls)

    _client("gemini-2.5-pro").generate(system="sys", user="hello", max_tokens=1000)

    _, config = calls[0]
    assert config.thinking_config.thinking_budget == 128


# ─── Fallback-on-quota-error logic ──────────────────────────────────────────

def test_fallback_to_flash_lite_on_quota_error(monkeypatch):
    calls = []
    _install_fake_genai(
        monkeypatch,
        {
            "gemini-2.5-flash": _FakeAPIError(429, "RESOURCE_EXHAUSTED"),
            "gemini-2.5-flash-lite": "Recovered via fallback",
        },
        calls,
    )

    result = _client("gemini-2.5-flash").generate(system="sys", user="hello", max_tokens=1000)

    assert result == "Recovered via fallback"
    assert [c[0] for c in calls] == ["gemini-2.5-flash", "gemini-2.5-flash-lite"]


def test_both_models_quota_exceeded_raises_clear_runtime_error(monkeypatch):
    calls = []
    _install_fake_genai(
        monkeypatch,
        {
            "gemini-2.5-flash": _FakeAPIError(429, "RESOURCE_EXHAUSTED"),
            "gemini-2.5-flash-lite": _FakeAPIError(429, "RESOURCE_EXHAUSTED"),
        },
        calls,
    )

    with pytest.raises(RuntimeError, match="quota exceeded on all available models"):
        _client("gemini-2.5-flash").generate(system="sys", user="hello", max_tokens=1000)

    assert [c[0] for c in calls] == ["gemini-2.5-flash", "gemini-2.5-flash-lite"]


def test_no_duplicate_attempt_when_configured_model_is_already_the_fallback(monkeypatch):
    calls = []
    _install_fake_genai(
        monkeypatch, {"gemini-2.5-flash-lite": _FakeAPIError(429, "RESOURCE_EXHAUSTED")}, calls
    )

    with pytest.raises(RuntimeError):
        _client("gemini-2.5-flash-lite").generate(system="sys", user="hello", max_tokens=1000)

    assert [c[0] for c in calls] == ["gemini-2.5-flash-lite"]


# ─── Auth errors fail fast, no wasted fallback attempt ─────────────────────

def test_auth_error_does_not_trigger_fallback(monkeypatch):
    calls = []
    _install_fake_genai(
        monkeypatch,
        {
            "gemini-2.5-flash": _FakeAPIError(403, "PERMISSION_DENIED: invalid API key"),
            "gemini-2.5-flash-lite": "should never be reached",
        },
        calls,
    )

    with pytest.raises(RuntimeError, match="Invalid Google API key"):
        _client("gemini-2.5-flash").generate(system="sys", user="hello", max_tokens=1000)

    assert [c[0] for c in calls] == ["gemini-2.5-flash"]
