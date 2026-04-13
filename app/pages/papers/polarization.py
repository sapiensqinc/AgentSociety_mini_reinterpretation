"""Paper: Polarization Experiment (Section 7.2).

Faithful reproduction of the original run_polarization.py from branch paper-polarization.
"""

import asyncio
import re
import random
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from app.config import require_api_key
from agentsociety2_lite.env import EnvBase, tool


NAMES = ["Alex", "Jordan", "Taylor", "Morgan", "Casey",
         "Riley", "Quinn", "Avery", "Cameron", "Dakota"]

DESCRIPTION = """
**논문 대응**: 논문 Section 7.2 "Polarization"을 직접 재현한 실험입니다.
논문에서는 1,000명의 에이전트로 미국 총기규제에 대한 의견 양극화를 시뮬레이션했습니다.
3가지 사회적 조건(통제/동질적 상호작용/이질적 상호작용)에서 의견이 어떻게 변화하는지 관찰하여,
에코 챔버 효과(동질적 집단에서 극화 심화)와 교차 노출 효과(이질적 집단에서 의견 완화)를 검증했습니다.

**논문 결과**: 통제 조건에서 39% 극화/33% 완화, 동질적 조건에서 52% 극화(에코 챔버),
이질적 조건에서 89% 완화/11% 반대 의견 수용이라는 결과를 보고했습니다.

**동작 원리**: 에이전트들에게 0-10 척도의 초기 의견을 부여합니다(0=반대, 10=찬성).
통제 조건에서는 자연스러운 토론을, 동질적 조건에서는 같은 편끼리,
이질적 조건에서는 반대편과 대화하도록 유도합니다.
대화 후 응답에서 숫자를 추출하여 의견을 업데이트하고,
중심(5)으로부터의 거리 변화로 극화/완화/불변을 판정합니다.

**해결하는 문제**: 소셜 미디어의 에코 챔버가 사회 양극화를 심화시킨다는 가설을 계산 실험으로 검증합니다.
소규모(10명)로도 논문의 대규모(1,000명) 실험과 유사한 경향을 재현할 수 있는지 확인합니다.
"""


# ── Environment (faithful to original PolarizationSocialSpace) ──

class PolarizationSocialSpace(EnvBase):
    """Social environment that tracks agent opinions and messaging."""

    def __init__(self, agent_profiles: list[dict]):
        super().__init__()
        self._opinions: dict[int, float] = {}
        self._chat_log: list[dict] = []
        self._agent_names: dict[int, str] = {}
        for p in agent_profiles:
            aid = p["id"]
            self._agent_names[aid] = p["name"]
            self._opinions[aid] = p.get("initial_opinion", 5.0)

    @tool(readonly=True, kind="observe")
    def get_agent_opinion(self, agent_id: int) -> str:
        """Get an agent's current opinion on gun control (0-10 scale)."""
        opinion = self._opinions.get(agent_id, 5.0)
        name = self._agent_names.get(agent_id, f"Agent{agent_id}")
        stance = "supports" if opinion > 5 else "opposes" if opinion < 5 else "is neutral on"
        return f"{name} {stance} gun control (score: {opinion:.1f}/10)"

    @tool(readonly=True, kind="observe")
    def get_all_opinions(self) -> str:
        """Get all agents' opinions on gun control."""
        lines = [f"{self._agent_names.get(aid, f'Agent{aid}')}: {op:.1f}/10"
                 for aid, op in sorted(self._opinions.items())]
        return "Gun control opinions:\n" + "\n".join(lines)

    @tool(readonly=False)
    def update_opinion(self, agent_id: int, new_opinion: float) -> str:
        """Update an agent's opinion on gun control (0-10 scale)."""
        old = self._opinions.get(agent_id, 5.0)
        self._opinions[agent_id] = max(0, min(10, new_opinion))
        name = self._agent_names.get(agent_id, f"Agent{agent_id}")
        return f"{name} opinion updated: {old:.1f} -> {new_opinion:.1f}"

    @tool(readonly=False)
    def send_message(self, from_id: int, to_id: int, message: str) -> str:
        """Send a message from one agent to another."""
        self._chat_log.append({"from": from_id, "to": to_id, "message": message})
        return f"Message sent from {self._agent_names.get(from_id)} to {self._agent_names.get(to_id)}"

    @tool(readonly=True, kind="statistics")
    def get_opinion_statistics(self) -> str:
        """Get statistics about opinion distribution."""
        opinions = list(self._opinions.values())
        avg = sum(opinions) / len(opinions)
        support = sum(1 for o in opinions if o > 6)
        oppose = sum(1 for o in opinions if o < 4)
        neutral = len(opinions) - support - oppose
        return (f"Opinion Stats: avg={avg:.1f}, support={support}, oppose={oppose}, "
                f"neutral={neutral}, messages={len(self._chat_log)}")

    def get_opinions_snapshot(self) -> dict[int, float]:
        return dict(self._opinions)


# ── Profile generation (faithful to original) ──

def _generate_profiles(n=10, seed=42):
    random.seed(seed)
    personalities = [
        "conservative and values traditional rights",
        "liberal and values public safety",
        "libertarian who prioritizes individual freedom",
        "moderate who weighs both sides carefully",
        "progressive who advocates for stricter regulations",
    ]
    profiles = []
    all_ids = list(range(1, n + 1))
    for i in range(n):
        aid = i + 1
        opinion = random.uniform(1.0, 4.0) if random.random() < 0.5 else random.uniform(6.0, 9.0)
        friends = random.sample([x for x in all_ids if x != aid], k=min(3, n - 1))
        profiles.append({
            "id": aid,
            "name": NAMES[i % len(NAMES)],
            "personality": random.choice(personalities),
            "initial_opinion": round(opinion, 1),
            "friends": friends,
        })
    return profiles


# ── UI ──

def render():
    st.header("Polarization Experiment (Paper Sec 7.2)")
    st.caption("Branch: `paper-polarization`")

    with st.expander("이 예제에 대하여", expanded=False):
        st.markdown(DESCRIPTION)

    n_agents = st.number_input("Agents", 4, 20, 10)
    n_rounds = st.number_input("Rounds", 1, 5, 2)
    seed = st.number_input("Random Seed", 0, 100, 42)

    conditions = st.multiselect(
        "Conditions",
        ["control", "homophilic", "heterogeneous"],
        default=["control", "homophilic", "heterogeneous"],
    )

    if st.button("Run Experiment") and conditions and require_api_key():
        profiles = _generate_profiles(n_agents, seed)
        all_results = {}
        progress = st.progress(0)

        for ci, cond in enumerate(conditions):
            st.subheader(f"Condition: {cond.upper()}")
            with st.spinner(f"Running {cond}..."):
                result = asyncio.run(_run_condition(cond, profiles, n_rounds))
                all_results[cond] = result
            progress.progress((ci + 1) / len(conditions))

        # Visualization
        st.markdown("---")
        st.subheader("Opinion Distribution (Before vs After)")

        tabs = st.tabs([c.capitalize() for c in all_results.keys()])
        for tab, (cond, result) in zip(tabs, all_results.items()):
            with tab:
                fig = go.Figure()
                initial = list(result["initial"].values())
                final = list(result["final"].values())

                fig.add_trace(go.Scatter(
                    x=initial, y=[1]*len(initial), mode="markers",
                    name="Before", marker=dict(size=12, color="#3498db"),
                ))
                fig.add_trace(go.Scatter(
                    x=final, y=[0]*len(final), mode="markers",
                    name="After", marker=dict(size=12, color="#e74c3c"),
                ))
                for ini, fin in zip(initial, final):
                    fig.add_annotation(
                        x=fin, y=0, ax=ini, ay=1, xref="x", yref="y",
                        axref="x", ayref="y", showarrow=True,
                        arrowhead=2, arrowsize=1, arrowcolor="#95a5a6", opacity=0.5,
                    )
                fig.update_layout(
                    xaxis=dict(title="Opinion (0=Oppose, 10=Support)", range=[-0.5, 10.5]),
                    yaxis=dict(visible=False, range=[-0.5, 1.5]),
                    height=250,
                )
                st.plotly_chart(fig, use_container_width=True)

                st.write(f"Polarized: **{result['polarized_pct']}%** | "
                         f"Moderated: **{result['moderated_pct']}%** | "
                         f"Unchanged: **{result['unchanged']}**")

        st.markdown("---")
        st.subheader("Comparison with Paper")
        paper = {"control": (39, 33), "homophilic": (52, None), "heterogeneous": (None, 89)}
        rows = []
        for cond in all_results:
            r = all_results[cond]
            pp, pm = paper.get(cond, (None, None))
            rows.append({
                "Condition": cond,
                "Polarized (%)": r["polarized_pct"],
                "Paper Polarized": pp or "-",
                "Moderated (%)": r["moderated_pct"],
                "Paper Moderated": pm or "-",
            })
        st.table(rows)


# ── Experiment logic (faithful to original run_condition) ──

async def _run_condition(condition, profiles, num_rounds):
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from datetime import datetime

    env = PolarizationSocialSpace(agent_profiles=profiles)
    agents = [PersonAgent(id=p["id"], profile={
        "name": p["name"], "personality": p["personality"],
        "background": f"Opinion on gun control: {p['initial_opinion']:.1f}/10 (0=oppose, 10=support)",
    }) for p in profiles]

    society = AgentSociety(agents=agents, env_router=CodeGenRouter(env_modules=[env]),
                           start_t=datetime.now())
    await society.init()
    initial = env.get_opinions_snapshot()

    for rnd in range(num_rounds):
        for p in profiles:
            aid = p["id"]

            if condition == "homophilic":
                # Select peer with same-side opinion (faithful to original)
                same = [pr["id"] for pr in profiles if pr["id"] != aid
                        and (initial[pr["id"]] > 5) == (initial[aid] > 5)]
                peer_id = random.choice(same) if same else random.choice(p["friends"])
                peer_name = env._agent_names.get(peer_id, f"Agent{peer_id}")
                msg = (f"You are {p['name']}. Your opinion on gun control: {initial[aid]:.1f}/10. "
                       f"You are talking with {peer_name} who AGREES with you on gun control. "
                       f"After discussion, state your updated opinion as a number 0-10.")

            elif condition == "heterogeneous":
                # Select peer with opposing opinion (faithful to original)
                opp = [pr["id"] for pr in profiles if pr["id"] != aid
                       and (initial[pr["id"]] > 5) != (initial[aid] > 5)]
                peer_id = random.choice(opp) if opp else random.choice(p["friends"])
                peer_name = env._agent_names.get(peer_id, f"Agent{peer_id}")
                msg = (f"You are {p['name']}. Your opinion on gun control: {initial[aid]:.1f}/10. "
                       f"You are talking with {peer_name} who DISAGREES with you on gun control. "
                       f"Listen carefully to their perspective. State your updated opinion as a number 0-10.")

            else:  # control
                msg = (f"You are {p['name']}. Your opinion on gun control: {initial[aid]:.1f}/10. "
                       f"Discuss gun control naturally. State your updated opinion as a number 0-10.")

            resp = await society.ask(msg)
            match = re.search(r"(\d+(?:\.\d+)?)", resp)
            if match:
                env._opinions[aid] = max(0, min(10, float(match.group(1))))

    final = env.get_opinions_snapshot()
    await society.close()

    polarized = moderated = unchanged = 0
    for aid in initial:
        d_init = abs(initial[aid] - 5)
        d_final = abs(final[aid] - 5)
        if d_final > d_init + 0.5:
            polarized += 1
        elif d_final < d_init - 0.5:
            moderated += 1
        else:
            unchanged += 1

    total = len(initial)
    return {
        "condition": condition,
        "polarized_pct": round(100 * polarized / total, 1),
        "moderated_pct": round(100 * moderated / total, 1),
        "unchanged": unchanged,
        "initial": {env._agent_names[k]: v for k, v in initial.items()},
        "final": {env._agent_names[k]: v for k, v in final.items()},
    }
