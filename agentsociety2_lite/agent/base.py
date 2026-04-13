"""AgentBase — abstract base class for LLM-backed agents."""

from typing import Any


class AgentBase:
    """Base class for all agents. Subclass and override ask() for custom behavior."""

    def __init__(self, id: int, profile: dict[str, Any] | None = None, **kwargs):
        self._id = id
        self._profile = profile or {}
        self._name = self._profile.get("name", f"Agent{id}")
        self._router = None

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    def set_router(self, router):
        self._router = router

    def _build_system_prompt(self) -> str:
        """Build a system prompt from profile. Override for customization."""
        parts = []
        if self._name:
            parts.append(f"You are {self._name}.")
        for key, value in self._profile.items():
            if key == "name":
                continue
            parts.append(f"Your {key}: {value}")
        return " ".join(parts)

    async def ask(self, question: str, readonly: bool = True) -> str:
        """Ask the agent a question via the router."""
        if self._router is None:
            raise RuntimeError(f"Agent {self._name} has no router. Call set_router() first.")
        system = self._build_system_prompt()
        return await self._router.route(question, system=system, readonly=readonly)
