"""Lightweight startup checks before a session begins."""

from __future__ import annotations

from pathlib import Path

from sopshield.providers.base import LLMProvider
from sopshield.providers.ollama import OllamaProvider
from sopshield.providers.rule import RuleBasedProvider
from sopshield.sop.loader import load_sop, resolve_sop_path
from sopshield.sop.validation import SOPLoadError, SOPValidationError

SUPPORTED_PROVIDERS = ("rule", "ollama", "openai")


class StartupError(Exception):
    """Fatal startup failure with a user-facing message."""


class MissingSOPError(StartupError):
    """SOP id or path could not be resolved to a file."""


class InvalidConfigurationError(StartupError):
    """SOP or runtime configuration is invalid."""


class UnsupportedProviderError(StartupError):
    """Provider name is not supported or cannot be initialized."""

    def __init__(self, provider: str, detail: str) -> None:
        self.provider = provider
        super().__init__(detail)

    def __str__(self) -> str:
        supported = ", ".join(SUPPORTED_PROVIDERS)
        return (
            f"Unsupported provider: {self.provider!r}\n\n"
            f"  {self.args[0]}\n\n"
            f"Supported providers: {supported}\n"
            f"Use --provider rule for offline, deterministic answers (default)."
        )


def validate_provider_name(provider: str) -> None:
    """Raise UnsupportedProviderError when the provider name is not recognized."""
    if provider not in SUPPORTED_PROVIDERS:
        raise UnsupportedProviderError(
            provider,
            f"Choose one of: {', '.join(SUPPORTED_PROVIDERS)}.",
        )


def build_provider(provider: str) -> LLMProvider:
    """Construct a provider after validating the selection."""
    validate_provider_name(provider)
    if provider == "rule":
        return RuleBasedProvider()
    if provider == "ollama":
        return OllamaProvider()
    if provider == "openai":
        try:
            from sopshield.providers.openai_api import OpenAIProvider
        except ImportError:
            raise UnsupportedProviderError(
                provider,
                "OpenAI support is optional. Install with: pip install sopshield[openai]",
            ) from None
        return OpenAIProvider()
    raise UnsupportedProviderError(provider, "Unknown provider.")


def validate_sop(sop: str | Path, data_dir: Path | None = None) -> Path:
    """Resolve and validate a SOP file; return the resolved path."""
    try:
        path = resolve_sop_path(sop, data_dir)
    except FileNotFoundError as exc:
        raise MissingSOPError(str(exc)) from exc

    try:
        load_sop(path)
    except SOPValidationError as exc:
        raise InvalidConfigurationError(str(exc)) from exc
    except SOPLoadError as exc:
        raise InvalidConfigurationError(str(exc)) from exc

    return path
