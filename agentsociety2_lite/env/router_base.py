"""Router base class — connects agents to environment tools via LLM."""

from typing import Any

from .env_base import EnvBase
from ..llm import LLMClient, get_client


class TokenUsageStats:
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0


class RouterBase:
    """Base class for routing strategies."""

    def __init__(self, env_modules: list[EnvBase] | None = None):
        self._modules: list[EnvBase] = env_modules or []
        self._llm: LLMClient | None = None
        self._replay_writer = None

    def register_module(self, module: EnvBase):
        self._modules.append(module)
        # Invalidate tool caches
        for m in self._modules:
            m._tools_cache = None

    def set_replay_writer(self, writer):
        self._replay_writer = writer

    def _get_llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = get_client()
        return self._llm

    def get_all_tools(self, readonly_only: bool = False) -> list[dict[str, Any]]:
        tools = []
        for module in self._modules:
            tools.extend(module.get_tools(readonly_only=readonly_only))
        return tools

    def call_tool(self, name: str, args: dict[str, Any]) -> str:
        for module in self._modules:
            method = getattr(module, name, None)
            if method is not None and getattr(method, "_is_tool", False):
                return module.call_tool(name, args)
        return f"Error: Tool '{name}' not found in any module"

    async def route(
        self,
        question: str,
        system: str = "",
        readonly: bool = True,
    ) -> str:
        raise NotImplementedError("Subclasses must implement route()")
