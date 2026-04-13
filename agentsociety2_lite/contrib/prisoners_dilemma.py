"""PrisonersDilemma — classic game theory environment."""

from ..env.env_base import EnvBase, tool


class PrisonersDilemma(EnvBase):
    """Prisoner's Dilemma game environment."""

    def __init__(
        self,
        cooperate_reward: int = 1,
        defect_punishment: int = 1,
        temptation: int = 3,
        sucker_punishment: int = 3,
    ):
        super().__init__()
        self.cooperate_reward = cooperate_reward
        self.defect_punishment = defect_punishment
        self.temptation = temptation
        self.sucker_punishment = sucker_punishment

    @tool(readonly=True, kind="observe")
    def get_payoff_matrix(self) -> str:
        """Get the payoff matrix for the prisoner's dilemma."""
        cc = self.cooperate_reward
        dd = self.defect_punishment
        t = self.temptation
        s = self.sucker_punishment
        return (
            f"Payoff Matrix (years in prison):\n"
            f"  Both Cooperate: {cc} year(s) each\n"
            f"  Both Defect: {cc + dd + 1} year(s) each\n"
            f"  Cooperator vs Defector: Cooperator gets {cc + s + 1} years, Defector goes free\n"
            f"  Temptation to defect: {t}, Sucker's payoff: -{s}"
        )

    @tool(readonly=True, kind="observe")
    def get_rules(self) -> str:
        """Get the rules of the prisoner's dilemma."""
        return (
            "You are in a prisoner's dilemma. You can either COOPERATE (stay silent) "
            "or DEFECT (betray your partner). You don't know what your partner will choose."
        )
