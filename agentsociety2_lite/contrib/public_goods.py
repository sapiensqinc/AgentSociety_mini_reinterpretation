"""PublicGoodsGame — multi-player contribution game."""

from ..env.env_base import EnvBase, tool


class PublicGoodsGame(EnvBase):
    """Public Goods Game environment."""

    def __init__(
        self,
        endowment: int = 100,
        contribution_factor: float = 1.5,
    ):
        super().__init__()
        self.endowment = endowment
        self.contribution_factor = contribution_factor

    @tool(readonly=True, kind="observe")
    def get_game_rules(self) -> str:
        """Get the rules of the public goods game."""
        return (
            f"Public Goods Game Rules:\n"
            f"- Each player starts with ${self.endowment}\n"
            f"- You can contribute any amount ($0 to ${self.endowment}) to the public good\n"
            f"- Total contributions are multiplied by {self.contribution_factor}x\n"
            f"- The multiplied amount is divided equally among all players\n"
            f"- Your payoff = (endowment - contribution) + (share of public good)"
        )

    @tool(readonly=True, kind="statistics")
    def get_endowment(self) -> str:
        """Get the current endowment amount."""
        return f"Each player has ${self.endowment} to allocate."
