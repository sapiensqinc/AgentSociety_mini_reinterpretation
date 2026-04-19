"""OpenAI-compatible LLM client — second track alongside Gemini.

Targets any OpenAI-compatible `/v1/chat/completions` endpoint:
- Self-hosted vLLM / TGI / Ollama (e.g. `http://localhost:8000/v1`)
- HuggingFace Inference Providers router (https://router.huggingface.co/v1)
- Mistral La Plateforme (https://api.mistral.ai/v1)
- OpenAI / Together / Fireworks / Groq / Cerebras

Recommended open-weights pairing (see README "LLM backends"):
  - Mistral Small (Apache 2.0, Korean supported, native tool-parser).
    Default env example: mistralai/Mistral-Small-3.1-24B-Instruct-2503
  - gpt-oss-120b (Apache 2.0, single-H100 via MoE).

Dependency: `httpx` only. No openai SDK, no litellm — keeps supply chain tight.
"""

import json
import os
from typing import Any

import httpx

from .base import LLMClient, MAX_OUTPUT_TOKENS


# Generous but bounded timeout — large tool-call responses can be slow on cold start.
_HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)


class OpenAICompatibleClient(LLMClient):
    """Minimal OpenAI-compatible client for chat/completions + tool use."""

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.api_base = (
            api_base
            or os.getenv("LLM_API_BASE", "")
            or "https://router.huggingface.co/v1"
        ).rstrip("/")
        self.model = (
            model
            or os.getenv("LLM_MODEL", "")
            or "mistralai/Mistral-Small-3.1-24B-Instruct-2503"
        )
        if not self.api_key:
            raise RuntimeError(
                "LLM API key not provided (LLM_API_KEY). "
                "Enter it via the sidebar or set the env var."
            )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_messages(self, prompt: str, system: str) -> list[dict[str, Any]]:
        msgs: list[dict[str, Any]] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    async def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": self._build_messages(prompt, system),
            "temperature": temperature,
            "max_tokens": MAX_OUTPUT_TOKENS,
        }
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as cli:
            r = await cli.post(
                f"{self.api_base}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        msg = choices[0].get("message") or {}
        return msg.get("content") or ""

    async def complete_with_tools(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        system: str = "",
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Emits OpenAI-spec `tools` array and parses `tool_calls` response.

        Returns {"text": str, "tool_calls": [{"name": str, "args": dict}, ...]}.
        Many providers (vLLM w/ --enable-auto-tool-choice, Mistral, Together)
        route this to native function calling. Providers that don't support
        tools natively will typically echo an empty tool_calls array and the
        caller should handle the "text" branch.
        """
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get(
                        "parameters",
                        {"type": "object", "properties": {}},
                    ),
                },
            }
            for t in tools
        ]

        payload = {
            "model": self.model,
            "messages": self._build_messages(prompt, system),
            "temperature": temperature,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "tools": openai_tools,
            "tool_choice": "auto",
        }

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as cli:
            r = await cli.post(
                f"{self.api_base}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            r.raise_for_status()
            data = r.json()

        result: dict[str, Any] = {"text": "", "tool_calls": []}
        choices = data.get("choices") or []
        if not choices:
            return result

        msg = choices[0].get("message") or {}
        result["text"] = msg.get("content") or ""

        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function") or {}
            name = fn.get("name") or ""
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
            except (json.JSONDecodeError, TypeError):
                args = {}
            if name:
                result["tool_calls"].append({"name": name, "args": args})

        return result
