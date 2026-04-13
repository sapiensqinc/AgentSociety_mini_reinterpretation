"""AgentSociety — orchestrator that connects agents with environment routers."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from ..agent.base import AgentBase
from ..env.router_base import RouterBase


class AgentSociety:
    """Orchestrator for running agent-based simulations."""

    def __init__(
        self,
        agents: list[AgentBase],
        env_router: RouterBase,
        start_t: datetime | None = None,
        replay_writer=None,
        **kwargs,
    ):
        self._agents = agents
        self._router = env_router
        self._start_t = start_t or datetime.now()
        self._current_t = self._start_t
        self._replay_writer = replay_writer
        self._initialized = False

    @property
    def current_time(self) -> datetime:
        return self._current_t

    @property
    def agents(self) -> list[AgentBase]:
        return self._agents

    async def init(self):
        """Initialize all agents with the router."""
        for agent in self._agents:
            agent.set_router(self._router)
        self._initialized = True

    async def ask(self, question: str) -> str:
        """Ask a question (readonly) through the first agent."""
        if not self._initialized:
            await self.init()

        # Use the first agent so the question gets the agent's profile context
        if self._agents:
            response = await self._agents[0].ask(question, readonly=True)
        else:
            response = await self._router.route(question, readonly=True)

        if self._replay_writer:
            await self._replay_writer.write_interaction(
                agent_id=self._agents[0]._id if self._agents else 0,
                prompt=question,
                response=response,
                timestamp=self._current_t,
            )

        return response

    async def intervene(self, action: str) -> str:
        """Perform a write action on the environment."""
        if not self._initialized:
            await self.init()
        return await self._router.route(action, readonly=False)

    async def run(self, num_steps: int = 10, tick: float = 1.0):
        """Run simulation for num_steps ticks.

        Each tick advances the simulation time and triggers agent forward() if defined.
        """
        if not self._initialized:
            await self.init()

        for step in range(num_steps):
            self._current_t = self._start_t + timedelta(seconds=step * tick)
            for agent in self._agents:
                if hasattr(agent, "forward"):
                    await agent.forward(self._current_t)

    async def close(self):
        """Clean up resources."""
        self._initialized = False
