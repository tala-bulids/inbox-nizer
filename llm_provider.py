"""Provider-neutral interface for chat language models."""

from typing import Protocol


class LLMProvider(Protocol):
    def generate(self, messages: list[dict[str, str]]) -> str:
        """Generate one grounded answer from chat messages."""
        ...