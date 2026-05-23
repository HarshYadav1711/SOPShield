"""Abstract LLM provider — swap local, rule-based, or optional cloud backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    confidence: float | None = None


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str) -> ProviderResponse:
        """Return assistant text for the given prompts."""
