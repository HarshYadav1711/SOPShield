"""Optional OpenAI-compatible API adapter (isolated; not required to run)."""

from __future__ import annotations

from sopshield.providers.base import LLMProvider, ProviderResponse


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "Install optional dependency: pip install sopshield[openai]"
            ) from exc
        self._client = OpenAI(api_key=api_key)
        self.model = model

    def complete(self, system: str, user: str) -> ProviderResponse:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        text = response.choices[0].message.content or ""
        return ProviderResponse(text=text.strip(), confidence=None)
