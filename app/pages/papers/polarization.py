"""Paper: Polarization Experiment (Section 7.2)."""

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
    for i in range(n):
        opinion = random.uniform(1.0, 4.0) if random.random() < 0.5 else random.uniform(6.0, 9.0)
        profiles.append({
            "id": i + 1, "name": NAMES[i % len(NAMES)],
            "personality": random.choice(personalities),
            "initial_opinion": round(opinion, 1),
        })
    return profiles


def render():
    st.header("Polarization Experiment (Paper Sec 7.2)")
    st.caption("Branch: `paper-polarization`")

    with st.expander("이 예제에 대하여", expanded=False):
        st.markdown("""
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
        """)

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
                names = list(result["initial"].keys())

                fig.add_trace(go.Scatter(
                    x=initial, y=[1]*len(initial), mode="markers",
                    name="Before", marker=dict(size=12, color="#3498db"),
                ))
                fig.add_trace(go.Scatter(
                    x=final, y=[0]*len(final), mode="markers",
                    name="After", marker=dict(size=12, color="#e74c3c"),
                ))
                # Arrows
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

        # Comparison table
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


async def _run_condition(condition, profiles, num_rounds):
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from agentsociety2_lite.env import EnvBase, tool
    from datetime import datetime

    initial = {p["name"]: p["initial_opinion"] for p in profiles}
    opinions = dict(initial)

    agents = [PersonAgent(id=p["id"], profile={
        "name": p["name"], "personality": p["personality"],
        "background": f"Opinion on gun control: {p['initial_opinion']:.1f}/10",
    }) for p in profiles]

    env = SimplePolarizationEnv(opinions)
    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=agents, env_router=router, start_t=datetime.now())
    await society.init()

    for rnd in range(num_rounds):
        for p in profiles:
            aid = p["id"]
            if condition == "homophilic":
                msg = (f"You are {p['name']}. Opinion: {opinions[p['name']]:.1f}/10. "
                       f"Talk with someone who AGREES with you. State your updated opinion 0-10.")
            elif condition == "heterogeneous":
                msg = (f"You are {p['name']}. Opinion: {opinions[p['name']]:.1f}/10. "
                       f"Talk with someone who DISAGREES. Listen carefully. Updated opinion 0-10.")
            else:
                msg = (f"You are {p['name']}. Opinion: {opinions[p['name']]:.1f}/10. "
                       f"Discuss gun control naturally. State your updated opinion 0-10.")

            resp = await society.ask(msg)
            match = re.search(r"(\d+(?:\.\d+)?)", resp)
            if match:
                opinions[p["name"]] = max(0, min(10, float(match.group(1))))

    await society.close()

    polarized = moderated = unchanged = 0
    for name in initial:
        d_init = abs(initial[name] - 5)
        d_final = abs(opinions[name] - 5)
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
        "initial": initial,
        "final": opinions,
    }


class SimplePolarizationEnv(EnvBase):
    def __init__(self, opinions):
        super().__init__()
        self._opinions = opinions

    @tool(readonly=True, kind="observe")
    def get_all_opinions(self) -> str:
        """Get all agents' opinions on gun control."""
        lines = [f"{name}: {op:.1f}/10" for name, op in self._opinions.items()]
        return "Opinions:\n" + "\n".join(lines)
