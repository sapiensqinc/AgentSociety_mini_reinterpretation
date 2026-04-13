"""SimpleSocialSpace — basic social environment with agent directory."""

from ..env.env_base import EnvBase, tool


class SimpleSocialSpace(EnvBase):
    """A simple social space where agents can discover each other."""

    def __init__(self, agent_id_name_pairs: list[tuple[int, str]] | None = None):
        super().__init__()
        self._agents: dict[int, str] = {}
        if agent_id_name_pairs:
            for aid, name in agent_id_name_pairs:
                self._agents[aid] = name

    @tool(readonly=True, kind="observe")
    def get_all_agents(self) -> str:
        """Get a list of all agents in the social space."""
        if not self._agents:
            return "No agents in the social space."
        lines = [f"- {name} (ID: {aid})" for aid, name in self._agents.items()]
        return "Agents in the social space:\n" + "\n".join(lines)

    @tool(readonly=True, kind="observe")
    def get_agent_info(self, agent_id: int) -> str:
        """Get information about a specific agent by ID."""
        name = self._agents.get(agent_id)
        if name is None:
            return f"No agent found with ID {agent_id}."
        return f"Agent {agent_id}: {name}"

    @tool(readonly=True, kind="statistics")
    def get_agent_count(self) -> str:
        """Get the total number of agents."""
        return f"Total agents: {len(self._agents)}"
