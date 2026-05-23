"""LLM provider interface — offline rule engine (default) or optional local/cloud adapters.

Workflow stages call complete() only where generative wording is needed (FAQ, optional
summary/handoff). Escalation and qualification do not use providers.
"""

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
