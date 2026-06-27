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
        "cost_info": "~$0.01–0.06 par génération selon le modèle. Pas de niveau gratuit.",
        "free": False,
        "doc_url": "https://console.anthropic.com/",
    },
    "Google (Gemini)": {
        "models": [
            "gemini-1.5-flash",             # gratuit, rapide
            "gemini-2.0-flash",             # gratuit, plus récent
            "gemini-1.5-pro",               # payant, haute qualité
        ],
        "cost_info": "Flash = gratuit (15 req/min, 1M tokens/jour). Pro = payant.",
        "free": True,
        "doc_url": "https://aistudio.google.com/app/apikey",
    },
    "Groq (Llama)": {
        "models": [
            "llama-3.1-8b-instant",         # gratuit, très rapide
            "llama-3.3-70b-versatile",      # gratuit, meilleure qualité
            "mixtral-8x7b-32768",           # gratuit, bon contexte
        ],
        "cost_info": "Entièrement gratuit (rate limits). Inférence ultra-rapide.",
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
                f"Fournisseur inconnu : '{provider}'. "
                f"Choix disponibles : {list(PROVIDERS.keys())}"
            )
        if not api_key or not api_key.strip():
            raise ValueError("La clé API est requise.")

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
            raise ValueError(f"Fournisseur non géré : {self.provider}")

    # ── Private: Anthropic ────────────────────────────────────────────────────

    def _anthropic(self, system: str, user: str, max_tokens: int) -> str:
        try:
            import anthropic
        except ImportError:
            raise ImportError("Lance : pip install anthropic")

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
                "Clé API Anthropic invalide. "
                "Vérifie sur https://console.anthropic.com/"
            )
        except anthropic.RateLimitError:
            raise RuntimeError(
                "Quota Anthropic dépassé. Attends quelques secondes et réessaie."
            )
        except Exception as e:
            raise RuntimeError(f"Erreur Anthropic API : {e}")

    # ── Private: Google Gemini ────────────────────────────────────────────────

    def _gemini(self, system: str, user: str, max_tokens: int) -> str:
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("Lance : pip install google-generativeai")

        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system,
            )
            response = model.generate_content(
                user,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7,
                ),
            )
            return response.text
        except Exception as e:
            err = str(e).lower()
            if "api_key" in err or "invalid" in err or "403" in err:
                raise RuntimeError(
                    "Clé API Google invalide. "
                    "Génère-en une sur https://aistudio.google.com/app/apikey"
                )
            if "quota" in err or "429" in err:
                raise RuntimeError(
                    "Quota Gemini dépassé. Attends 1 minute (tier gratuit : 15 req/min)."
                )
            raise RuntimeError(f"Erreur Gemini API : {e}")

    # ── Private: Groq ─────────────────────────────────────────────────────────

    def _groq(self, system: str, user: str, max_tokens: int) -> str:
        try:
            from groq import Groq
        except ImportError:
            raise ImportError("Lance : pip install groq")

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
                    "Clé API Groq invalide. "
                    "Vérifie sur https://console.groq.com/keys"
                )
            if "rate" in err or "429" in err:
                raise RuntimeError(
                    "Quota Groq dépassé. Attends quelques secondes."
                )
            raise RuntimeError(f"Erreur Groq API : {e}")
