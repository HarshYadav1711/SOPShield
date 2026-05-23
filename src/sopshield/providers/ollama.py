"""Optional local Ollama adapter (free, runs on your machine)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from sopshield.providers.base import LLMProvider, ProviderResponse


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://127.0.0.1:11434",
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    def complete(self, system: str, user: str) -> ProviderResponse:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": 0.2},
        }
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Ollama not reachable at {self.base_url}. "
                "Install Ollama and run `ollama serve`, or use --provider rule."
            ) from exc
        text = data.get("message", {}).get("content", "").strip()
        return ProviderResponse(text=text, confidence=None)
