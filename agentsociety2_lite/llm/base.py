"""Abstract LLM client base.

Two-track design:
- GeminiClient (google-genai SDK, default) — safer supply chain, remote only.
- OpenAICompatibleClient (httpx) — any OpenAI-compatible endpoint:
  self-hosted vLLM/TGI/Ollama, HuggingFace Inference Providers, Mistral La Plateforme, etc.

Both implementations share the same public API so callers (router_base, skills)
are backend-agnostic. Selection is driven by the LLM_BACKEND env var.
"""

from abc import ABC, abstractmethod
from typing import Any


# Hard cap on output tokens to prevent runaway generation. Shared across backends.
MAX_OUTPUT_TOKENS = 2048


class LLMClient(ABC):
    """Abstract LLM client interface.

    Concrete implementations must expose `complete` and `complete_with_tools`
    with identical semantics. Both are async and return plain Python data.
    """

    model: str

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
    ) -> str:
        """Single text completion."""

    @abstractmethod
    async def complete_with_tools(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        system: str = "",
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Completion with function-calling tools.

        Returns {"text": str, "tool_calls": [{"name": str, "args": dict}, ...]}.
        """
