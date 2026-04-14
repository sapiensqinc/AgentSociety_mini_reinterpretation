"""03. Reputation Game — indirect reciprocity with social norms.

Faithful reproduction of the original 03_reputation_game.py from branch examples-games,
using a proper ReputationGameEnv with @tool-decorated methods matching the original
ReputationGameEnv from agentsociety2/contrib/env/reputation_game.py.
"""

import asyncio
import random
import streamlit as st
import plotly.graph_objects as go
from app.config import require_api_key
from app.security import ready_to_run, cap, show_safe_error
from agentsociety2_lite.env import EnvBase, tool


PERSONALITIES = [
    "rational and cautious", "emotional", "fair-minded",
    "altruistic", "selfish", "vengeful", "optimistic", "pessimistic",
]

DESCRIPTION = """
**논문 대응**: 논문 Section 3.4 "Social Behaviors"의 사회적 상호작용 메커니즘과
Section 4.3 "Social Space"의 평판 기반 사회 네트워크를 결합한 실험입니다.
논문에서 에이전트들은 관계 강도에 따라 상호작용 빈도가 달라지는데,
이 예제는 그 기초가 되는 "간접 상호성(indirect reciprocity)" 이론을 구현합니다.

**원본 코드 위치**: `agentsociety2/contrib/env/reputation_game.py`의 `ReputationGameEnv`와
`agentsociety2/contrib/agent/llm_donor_agent.py`의 `LLMDonorAgent`가 원본입니다.
원본은 mem0 메모리 시스템과 연동하여 에이전트가 과거 상호작용을 기억하지만,
이 경량 버전에서는 전역 평판 상태로 단순화했습니다.

**동작 원리**: 매 스텝마다 무작위로 기여자-수혜자 쌍이 매칭됩니다. 기여자는 상대의 평판을 보고
협력(비용 지불, 상대에게 이익) 또는 배신(아무 일도 안 함)을 결정합니다.
사회 규범(Stern Judging, Image Score, Simple Standing)에 따라 이 결정이 기여자의 평판을 업데이트합니다.
예를 들어 Stern Judging에서는 "나쁜 평판인 상대를 배신하면 좋은 평판을 유지"하는 규칙이 적용됩니다.

**해결하는 문제**: 사회 규범이 집단 협력의 진화에 어떤 영향을 미치는지 탐구합니다.
진화 게임이론에서 Stern Judging이 Image Score보다 높은 협력률을 유도하는 것으로 알려져 있는데,
LLM 에이전트도 동일한 패턴을 보이는지 검증할 수 있습니다.
"""


# ── Environment (faithful to original ReputationGameEnv) ──

class ReputationGameEnv(EnvBase):
    """Reputation game environment matching original agentsociety2 contrib module."""

    def __init__(self, z: int, benefit: float, cost: float, norm_type: str, seed: int = 42):
        super().__init__()
        self._z = z
        self._benefit = benefit
        self._cost = cost
        self._norm_type = norm_type
        self._rng = random.Random(seed)

        # State
        self._reputations: dict[int, str] = {i: "good" for i in range(z)}
        self._payoffs: dict[int, float] = {i: 0.0 for i in range(z)}
        self._history: list[dict] = []
        self._cooperation_count = 0
        self._defection_count = 0

    @tool(readonly=True, kind="observe")
    def get_agent_reputation(self, agent_id: int) -> str:
        """Get the reputation of a specific agent."""
        rep = self._reputations.get(agent_id, "unknown")
        return f"Agent {agent_id} has a {rep} reputation."

    @tool(readonly=True, kind="observe")
    def get_agent_payoff(self, agent_id: int) -> str:
        """Get the accumulated payoff of a specific agent."""
        payoff = self._payoffs.get(agent_id, 0.0)
        return f"Agent {agent_id} payoff: {payoff:.1f}"

    @tool(readonly=True, kind="observe")
    def get_matchup_info(self, donor_id: int, recipient_id: int) -> str:
        """Get information about a donor-recipient matchup."""
        d_rep = self._reputations.get(donor_id, "unknown")
        r_rep = self._reputations.get(recipient_id, "unknown")
        return (f"Donor Agent {donor_id} (rep: {d_rep}) meets Recipient Agent {recipient_id} (rep: {r_rep}). "
                f"COOPERATE costs {self._cost} to donor, gives {self._benefit} to recipient. "
                f"DEFECT has no effect.")

    @tool(readonly=False)
    def submit_decision(self, donor_id: int, recipient_id: int, cooperate: bool) -> str:
        """Submit the donor's cooperation decision."""
        r_rep = self._reputations.get(recipient_id, "good")

        if cooperate:
            self._payoffs[donor_id] -= self._cost
            self._payoffs[recipient_id] += self._benefit
            self._cooperation_count += 1
        else:
            self._defection_count += 1

        # Update reputation based on norm
        if self._norm_type == "stern_judging":
            if cooperate and r_rep == "good":
                self._reputations[donor_id] = "good"
            elif cooperate and r_rep == "bad":
                self._reputations[donor_id] = "bad"
            elif not cooperate and r_rep == "good":
                self._reputations[donor_id] = "bad"
            else:  # defect against bad
                self._reputations[donor_id] = "good"
        elif self._norm_type == "image_score":
            self._reputations[donor_id] = "good" if cooperate else "bad"
        else:  # simple_standing
            if cooperate:
                self._reputations[donor_id] = "good"
            elif r_rep == "good":
                self._reputations[donor_id] = "bad"

        action = "COOPERATE" if cooperate else "DEFECT"
        self._history.append({
            "donor": donor_id, "recipient": recipient_id,
            "action": action, "donor_rep": self._reputations[donor_id],
            "recipient_rep": r_rep,
        })

        new_rep = self._reputations[donor_id]
        return f"Agent {donor_id} chose to {action}. New reputation: {new_rep}."

    @tool(readonly=True, kind="statistics")
    def get_global_statistics(self) -> str:
        """Get global game statistics."""
        total = self._cooperation_count + self._defection_count
        rate = self._cooperation_count / total if total > 0 else 0
        good = sum(1 for r in self._reputations.values() if r == "good")
        bad = self._z - good
        avg_payoff = sum(self._payoffs.values()) / self._z if self._z > 0 else 0
        return (f"Total interactions: {total}, Cooperations: {self._cooperation_count}, "
                f"Defections: {self._defection_count}, Cooperation rate: {rate:.2%}, "
                f"Good rep: {good}, Bad rep: {bad}, Avg payoff: {avg_payoff:.2f}")

    @tool(readonly=True, kind="statistics")
    def get_reputation_distribution(self) -> str:
        """Get the distribution of good vs bad reputations."""
        good = sum(1 for r in self._reputations.values() if r == "good")
        bad = self._z - good
        return f"Good: {good} ({100*good/self._z:.0f}%), Bad: {bad} ({100*bad/self._z:.0f}%)"

    @tool(readonly=True, kind="observe")
    def get_public_action_log(self, limit: int) -> str:
        """Get recent public action log entries."""
        recent = self._history[-limit:] if limit > 0 else self._history
        lines = [
            f"Agent{e['donor']}({e['donor_rep'][0].upper()}) -> "
            f"Agent{e['recipient']}({e['recipient_rep'][0].upper()}): {e['action']}"
            for e in recent
        ]
        return "\n".join(lines) if lines else "No interactions yet."


# ── UI ──

def render():
    st.header("03. Reputation Game")
    st.caption("Branch: `examples-games`")

    with st.expander("이 예제에 대하여", expanded=False):
        st.markdown(DESCRIPTION)

    col1, col2, col3 = st.columns(3)
    z = cap("agents", col1.number_input("Population (Z)", 4, 20, 8))
    benefit = col2.number_input("Benefit", 1, 20, 5)
    cost = col3.number_input("Cost", 1, 10, 1)
    norm = st.selectbox("Social Norm", ["stern_judging", "image_score", "simple_standing"])
    steps = cap("steps", st.slider("Simulation Steps", 5, 30, 10))

    if st.button("Run Simulation") and ready_to_run(tag="reputation_game"):
        with st.spinner(f"Running {steps} steps with {z} agents..."):
            try:
                results = asyncio.run(_run_reputation(z, benefit, cost, norm, steps))
            except Exception as e:
                show_safe_error(e, context="Failed to run simulation")
                return

        col_net, col_chart = st.columns([1, 1])

        with col_net:
            st.subheader("Reputation Distribution")
            good = sum(1 for r in results["reputations"].values() if r == "good")
            bad = z - good

            fig = go.Figure(data=[go.Pie(
                labels=["Good", "Bad"], values=[good, bad],
                marker_colors=["#2ecc71", "#e74c3c"],
            )])
            fig.update_layout(height=250, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with col_chart:
            st.subheader("Cooperation Rate Over Time")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=list(range(1, len(results["coop_history"]) + 1)),
                y=results["coop_history"],
                mode="lines+markers",
                fill="tozeroy",
                line=dict(color="#3498db"),
            ))
            fig.update_layout(
                yaxis_title="Cooperation Rate",
                yaxis=dict(range=[0, 1]),
                xaxis_title="Step", height=250,
                margin=dict(l=0, r=0, t=30, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

        # Statistics
        st.subheader("Global Statistics")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        total = results["stats"]["total"]
        col_s1.metric("Total Interactions", total)
        col_s2.metric("Cooperation Rate", f"{results['stats']['coop_rate']:.0%}")
        col_s3.metric("Avg Payoff", f"{results['stats']['avg_payoff']:.2f}")
        col_s4.metric("Good Rep Ratio", f"{results['stats']['good_ratio']:.0%}")

        st.subheader("Leaderboard")
        sorted_agents = sorted(results["payoffs"].items(), key=lambda x: x[1], reverse=True)
        for rank, (name, payoff) in enumerate(sorted_agents, 1):
            rep = results["reputations"][name]
            icon = "(+)" if rep == "good" else "(-)"
            st.write(f"{rank}. {icon} **{name}**: payoff = {payoff:.1f}")

        with st.expander("Recent Interactions"):
            for log in results["logs"][-15:]:
                st.text(log)


# ── Experiment logic (using ReputationGameEnv with @tool methods) ──

async def _run_reputation(z, benefit, cost, norm, steps):
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from datetime import datetime

    random.seed(42)

    # Create environment
    env = ReputationGameEnv(z=z, benefit=benefit, cost=cost, norm_type=norm, seed=42)

    # Create agents with diverse personalities
    agents = []
    for i in range(z):
        personality = random.choice(PERSONALITIES)
        agents.append(PersonAgent(
            id=i, profile={
                "name": f"Agent{i}",
                "personality": personality,
                "custom_fields": {"learning_frequency": 5, "personality": personality},
            }
        ))

    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=agents, env_router=router, start_t=datetime.now())
    await society.init()

    coop_history = []
    logs = []

    for step in range(steps):
        # Random donor-recipient pair
        ids = list(range(z))
        random.shuffle(ids)
        donor_id, recip_id = ids[0], ids[1]
        donor_name = f"Agent{donor_id}"
        recip_name = f"Agent{recip_id}"
        recip_rep = env._reputations[recip_id]

        # Ask via society (includes agent profile context)
        decision = await society.ask(
            f"You are {donor_name}. You meet {recip_name} whose reputation is {recip_rep}. "
            f"If you COOPERATE, you pay {cost} and they gain {benefit}. "
            f"If you DEFECT, nothing happens. "
            f"The social norm is '{norm}'. Choose COOPERATE or DEFECT and explain briefly."
        )
        cooperated = "cooperate" in decision.lower()

        # Submit decision through the environment tool
        env.call_tool("submit_decision", {
            "donor_id": donor_id,
            "recipient_id": recip_id,
            "cooperate": cooperated,
        })

        action = "COOPERATE" if cooperated else "DEFECT"
        logs.append(
            f"Step {step+1}: {donor_name}({env._reputations[donor_id][0].upper()}) -> "
            f"{recip_name}({recip_rep[0].upper()}): {action}"
        )

        good_count = sum(1 for r in env._reputations.values() if r == "good")
        coop_history.append(good_count / z)

    await society.close()

    total = env._cooperation_count + env._defection_count
    return {
        "reputations": {f"Agent{k}": v for k, v in env._reputations.items()},
        "payoffs": {f"Agent{k}": v for k, v in env._payoffs.items()},
        "coop_history": coop_history,
        "logs": logs,
        "stats": {
            "total": total,
            "coop_rate": env._cooperation_count / total if total > 0 else 0,
            "avg_payoff": sum(env._payoffs.values()) / z,
            "good_ratio": sum(1 for r in env._reputations.values() if r == "good") / z,
        },
    }
