"""
llm_client.py — Unified interface for multiple LLM providers.
Supported: Anthropic (Claude), Google (Gemini), Groq (Llama / Mixtral)
"""

from typing import Optional

# ─── Provider registry ────────────────────────────────────────────────────────

PROVIDERS: dict[str, dict] = {
    "Anthropic (Claude)": {
        "models": [
            "claude-3-5-haiku-20241022",    # fastest, cheapest
            "claude-3-5-sonnet-20241022",   # balanced
            "claude-opus-4-5",              # most capable
        ],
        "cost_info": "~$0.01-0.06 per generation depending on the model. No free tier.",
        "free": False,
        "doc_url": "https://console.anthropic.com/",
    },
    "Google (Gemini)": {
        "models": [
            "gemini-2.5-flash",             # free tier, fast
            "gemini-2.5-flash-lite",        # free tier, more generous quota
            "gemini-2.5-pro",               # paid, high quality
        ],
        "cost_info": "Flash models have a free tier (rate-limited). Pro is paid.",
        "free": True,
        "doc_url": "https://aistudio.google.com/app/apikey",
    },
    "Groq (Llama)": {
        "models": [
            "llama-3.1-8b-instant",         # free, very fast
            "llama-3.3-70b-versatile",      # free, better quality
            "mixtral-8x7b-32768",           # free, good context
        ],
        "cost_info": "Entirely free (rate limited). Ultra-fast inference.",
        "free": True,
        "doc_url": "https://console.groq.com/keys",
    },
}


# ─── Client ───────────────────────────────────────────────────────────────────

class LLMClient:
    """
    Unified LLM client. Abstracts provider-specific SDKs behind a single
    `generate(system, user, max_tokens)` interface.

    Args:
        provider: One of the keys in PROVIDERS
        api_key: Provider API key
        model: Model name (must match provider's model list)
    """

    def __init__(self, provider: str, api_key: str, model: str):
        if provider not in PROVIDERS:
            raise ValueError(
                f"Unknown provider: '{provider}'. "
                f"Available choices: {list(PROVIDERS.keys())}"
            )
        if not api_key or not api_key.strip():
            raise ValueError("The API key is required.")

        self.provider = provider
        self.api_key = api_key.strip()
        self.model = model

    # ── Public ────────────────────────────────────────────────────────────────

    def generate(
        self,
        system: str,
        user: str,
        max_tokens: int = 4000,
    ) -> str:
        """
        Generate a response from the configured LLM.

        Args:
            system: System prompt (persona / instructions)
            user: User message (the actual request)
            max_tokens: Maximum tokens in the response

        Returns:
            str: Model's text response

        Raises:
            RuntimeError: On API errors (auth, quota, network)
        """
        if "Anthropic" in self.provider:
            return self._anthropic(system, user, max_tokens)
        elif "Google" in self.provider:
            return self._gemini(system, user, max_tokens)
        elif "Groq" in self.provider:
            return self._groq(system, user, max_tokens)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    # ── Private: Anthropic ────────────────────────────────────────────────────

    def _anthropic(self, system: str, user: str, max_tokens: int) -> str:
        try:
            import anthropic
        except ImportError:
            raise ImportError("Run: pip install anthropic")

        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            message = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return message.content[0].text
        except anthropic.AuthenticationError:
            raise RuntimeError(
                "Invalid Anthropic API key. "
                "Check it at https://console.anthropic.com/"
            )
        except anthropic.RateLimitError:
            raise RuntimeError(
                "Anthropic quota exceeded. Wait a few seconds and try again."
            )
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {e}")

    # ── Private: Google Gemini ────────────────────────────────────────────────

    _GEMINI_FALLBACK_MODEL = "gemini-2.5-flash-lite"

    @staticmethod
    def _gemini_thinking_budget(model_name: str) -> int:
        """0 fully disables "thinking" (supported by flash / flash-lite —
        this is what was silently eating the max_output_tokens budget and
        truncating responses). gemini-2.5-pro requires a minimum non-zero
        budget and can't have thinking disabled outright."""
        return 128 if "pro" in model_name else 0

    @staticmethod
    def _gemini_error_code(e: Exception) -> int | None:
        """google.genai.errors.APIError exposes a structured .code (HTTP
        status); fall back to None for anything else so callers can still
        use string matching as a second line of defense."""
        return getattr(e, "code", None)

    def _gemini(self, system: str, user: str, max_tokens: int) -> str:
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError("Run: pip install google-genai")

        client = genai.Client(api_key=self.api_key)

        # Try the configured model first, then fall back to a more generous
        # free-tier model on quota errors only (auth/other errors won't be
        # fixed by switching models, so they fail fast instead).
        models_to_try = [self.model]
        if self.model != self._GEMINI_FALLBACK_MODEL:
            models_to_try.append(self._GEMINI_FALLBACK_MODEL)

        last_error: Exception | None = None
        for attempt, model_name in enumerate(models_to_try):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=user,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        max_output_tokens=max_tokens,
                        temperature=0.7,
                        thinking_config=types.ThinkingConfig(
                            thinking_budget=self._gemini_thinking_budget(model_name),
                        ),
                    ),
                )
                return response.text
            except Exception as e:
                last_error = e
                code = self._gemini_error_code(e)
                err = str(e).lower()
                is_quota_error = code == 429 or "429" in err or "quota" in err or "resource exhausted" in err
                is_last_attempt = attempt == len(models_to_try) - 1
                if is_quota_error and not is_last_attempt:
                    continue
                break

        code = self._gemini_error_code(last_error)
        err = str(last_error).lower()
        if code in (401, 403) or "api_key" in err or "invalid" in err or "403" in err:
            raise RuntimeError(
                "Invalid Google API key. "
                "Generate one at https://aistudio.google.com/app/apikey"
            )
        if code == 429 or "429" in err or "quota" in err or "resource exhausted" in err:
            tried = ", ".join(models_to_try)
            raise RuntimeError(
                f"Gemini quota exceeded on all available models ({tried}). "
                "Wait a few minutes and try again, or check https://ai.dev/rate-limit."
            )
        raise RuntimeError(f"Gemini API error: {last_error}")

    # ── Private: Groq ─────────────────────────────────────────────────────────

    def _groq(self, system: str, user: str, max_tokens: int) -> str:
        try:
            from groq import Groq
        except ImportError:
            raise ImportError("Run: pip install groq")

        try:
            client = Groq(api_key=self.api_key)
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=0.7,
            )
            return completion.choices[0].message.content
        except Exception as e:
            err = str(e).lower()
            if "auth" in err or "invalid" in err or "401" in err:
                raise RuntimeError(
                    "Invalid Groq API key. "
                    "Check it at https://console.groq.com/keys"
                )
            if "rate" in err or "429" in err:
                raise RuntimeError(
                    "Groq quota exceeded. Wait a few seconds."
                )
            raise RuntimeError(f"Groq API error: {e}")
