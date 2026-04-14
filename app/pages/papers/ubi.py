"""Paper: UBI Experiment (Section 7.4)."""

import asyncio
import re
import random
from typing import Dict, List
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from app.config import require_api_key
from app.security import ready_to_run, cap, show_safe_error
from agentsociety2_lite.env import EnvBase, tool


OCCUPATIONS = ["retail worker", "teacher", "nurse", "truck driver",
               "software engineer", "construction worker", "cashier", "waiter"]

DESCRIPTION = """
**논문 대응**: 논문 Section 7.4 "Universal Basic Income"을 재현한 실험입니다.
논문에서는 텍사스주 주민 프로필 기반으로 월 $1,000 UBI 지급 시나리오를 시뮬레이션하여,
소비 수준, 저축, 우울증(행복도) 변화를 UBI 미지급 조건과 비교했습니다.
이 실험은 논문 Section 4.4 "Economic Space"의 경제 환경 모듈과 연동됩니다.

**논문 결과**: UBI 지급 시 소비 수준이 증가하고 우울증 수준이 감소했습니다.
에이전트 인터뷰에서는 금리에 대한 우려, 장기적 혜택에 대한 기대,
저축 습관 변화 등 현실적인 반응이 관찰되었습니다.

**동작 원리**: 8명의 에이전트에게 다양한 직업(소매업, 교사, 간호사 등)과
소득 수준($1,200~$8,000)을 부여합니다. 매월 가처분소득(급여 + UBI)을 알려주고
지출액과 행복도를 결정하도록 합니다. 응답에서 금액과 행복도 점수를 파싱하여 경제 지표를 추적합니다.
UBI 조건에서는 추가로 정책에 대한 인터뷰를 실시합니다.

**해결하는 문제**: 대규모 정책 실험이 현실에서 불가능할 때 LLM 에이전트로 사전 시뮬레이션합니다.
UBI 외에도 최저임금 인상, 세금 정책 등 다양한 경제 정책의 효과를 실험 전에 예측하는 용도로 확장할 수 있습니다.
"""


def _generate_profiles(n=8, seed=42):
    random.seed(seed)
    return [{
        "id": i + 1, "name": f"Resident_{i+1}",
        "occupation": OCCUPATIONS[i % len(OCCUPATIONS)],
        "income": round(max(1200, min(8000, random.gauss(3500, 1500)))),
        "savings": round(random.uniform(1000, 15000)),
        "happiness": round(random.uniform(3, 7), 1),
    } for i in range(n)]


class EconomyEnv(EnvBase):
    """Simplified economic environment for UBI experiment.

    Faithfully reproduces EconomySpace from the original paper script,
    with all 4 @tool methods: get_economic_status, make_consumption_decision,
    update_happiness, get_economy_statistics.
    """

    def __init__(self, agent_profiles: List[Dict], ubi_amount: float = 0):
        super().__init__()
        self._names: Dict[int, str] = {}
        self._income: Dict[int, float] = {}
        self._savings: Dict[int, float] = {}
        self._consumption: Dict[int, float] = {}
        self._happiness: Dict[int, float] = {}
        self._ubi = ubi_amount

        for p in agent_profiles:
            aid = p["id"]
            self._names[aid] = p["name"]
            self._income[aid] = p.get("income", 3000)
            self._savings[aid] = p.get("savings", 5000)
            self._consumption[aid] = 0
            self._happiness[aid] = p.get("happiness", 5.0)

    @tool(readonly=True, kind="observe")
    def get_economic_status(self, agent_id: int) -> str:
        """Get agent economic status."""
        name = self._names.get(agent_id, f"Agent{agent_id}")
        disposable = self._income[agent_id] + self._ubi
        return (
            f"{name}: income=${self._income[agent_id]:.0f}, "
            f"UBI=${self._ubi:.0f}, disposable=${disposable:.0f}, "
            f"savings=${self._savings[agent_id]:.0f}, happiness={self._happiness[agent_id]:.1f}/10"
        )

    @tool(readonly=False)
    def make_consumption_decision(self, agent_id: int, amount: float) -> str:
        """Agent decides to spend a certain amount."""
        disposable = self._income[agent_id] + self._ubi
        actual = min(amount, disposable + self._savings[agent_id])
        self._consumption[agent_id] += actual
        self._savings[agent_id] += (disposable - actual)
        name = self._names[agent_id]
        return f"{name} spent ${actual:.0f}. Remaining savings: ${self._savings[agent_id]:.0f}"

    @tool(readonly=False)
    def update_happiness(self, agent_id: int, score: float) -> str:
        """Update agent happiness/wellbeing score (0-10)."""
        self._happiness[agent_id] = max(0, min(10, score))
        return f"{self._names[agent_id]} happiness: {score:.1f}/10"

    @tool(readonly=True, kind="statistics")
    def get_economy_statistics(self) -> str:
        """Get aggregate economic statistics."""
        n = len(self._names)
        avg_consumption = sum(self._consumption.values()) / n
        avg_savings = sum(self._savings.values()) / n
        avg_happiness = sum(self._happiness.values()) / n
        gdp = sum(self._consumption.values())
        return (
            f"GDP: ${gdp:.0f}, Avg consumption: ${avg_consumption:.0f}, "
            f"Avg savings: ${avg_savings:.0f}, Avg happiness: {avg_happiness:.1f}/10"
        )

    def get_metrics(self) -> Dict:
        n = len(self._names)
        return {
            "avg_consumption": sum(self._consumption.values()) / n,
            "avg_savings": sum(self._savings.values()) / n,
            "avg_happiness": sum(self._happiness.values()) / n,
            "gdp": sum(self._consumption.values()),
        }


def render():
    st.header("UBI Experiment (Paper Sec 7.4)")
    st.caption("Branch: `paper-ubi`")

    with st.expander("이 예제에 대하여", expanded=False):
        st.markdown(DESCRIPTION)

    n_agents = cap("agents", st.number_input("Agents", 4, 16, 8))
    ubi_amount = st.number_input("UBI Amount ($/month)", 0, 5000, 1000, 100)
    months = cap("rounds", st.number_input("Months", 1, 6, 3))

    profiles = _generate_profiles(n_agents)

    with st.expander("Agent Profiles"):
        st.dataframe([{
            "Name": p["name"], "Occupation": p["occupation"],
            "Income": f"${p['income']}", "Savings": f"${p['savings']}",
            "Happiness": p["happiness"],
        } for p in profiles])

    if st.button("Run Experiment") and ready_to_run(tag="ubi"):
        with st.spinner("Running No UBI condition..."):
            try:
                r_no = asyncio.run(_run_ubi(profiles, 0, months))
            except Exception as e:
                show_safe_error(e, context="Failed to run No UBI condition")
                return
        with st.spinner("Running UBI condition..."):
            try:
                r_yes = asyncio.run(_run_ubi(profiles, ubi_amount, months))
            except Exception as e:
                show_safe_error(e, context="Failed to run UBI condition")
                return

        # Charts
        st.markdown("---")
        fig = make_subplots(rows=1, cols=2, subplot_titles=["Avg Consumption", "Avg Happiness"])

        for label, result, color in [("No UBI", r_no, "#e74c3c"), (f"UBI ${ubi_amount}", r_yes, "#2ecc71")]:
            months_x = list(range(1, len(result["metrics"]) + 1))
            fig.add_trace(go.Scatter(
                x=months_x, y=[m["avg_consumption"] for m in result["metrics"]],
                name=f"{label} (consumption)", line=dict(color=color),
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=months_x, y=[m["avg_happiness"] for m in result["metrics"]],
                name=f"{label} (happiness)", line=dict(color=color, dash="dash"),
            ), row=1, col=2)

        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

        # Summary metrics
        st.subheader("Summary")
        col1, col2, col3 = st.columns(3)
        f_no, f_yes = r_no["final"], r_yes["final"]
        col1.metric("Avg Consumption", f"${f_yes['avg_consumption']:.0f}",
                     f"+${f_yes['avg_consumption'] - f_no['avg_consumption']:.0f}")
        col2.metric("Avg Savings", f"${f_yes['avg_savings']:.0f}",
                     f"+${f_yes['avg_savings'] - f_no['avg_savings']:.0f}")
        col3.metric("Avg Happiness", f"{f_yes['avg_happiness']:.1f}",
                     f"+{f_yes['avg_happiness'] - f_no['avg_happiness']:.1f}")

        # Interviews
        if r_yes.get("interviews"):
            st.subheader("Agent Interviews (UBI condition)")
            for iv in r_yes["interviews"]:
                with st.chat_message("assistant"):
                    st.markdown(f"**{iv['agent']}:**")
                    st.write(iv["response"][:300])

        st.caption("Paper: UBI increases consumption, reduces depression")


async def _run_ubi(profiles, ubi, num_months):
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from datetime import datetime

    env = EconomyEnv(agent_profiles=profiles, ubi_amount=ubi)
    agents = [PersonAgent(id=p["id"], profile={
        "name": p["name"],
        "personality": f"a {p['occupation']} trying to make ends meet",
        "background": f"Monthly income: ${p['income']}, Savings: ${p['savings']}",
    }) for p in profiles]

    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=agents, env_router=router, start_t=datetime.now())
    await society.init()

    metrics = []
    for month in range(1, num_months + 1):
        for p in profiles:
            disposable = p["income"] + ubi
            resp = await society.ask(
                f"You are {p['name']}, a {p['occupation']}. "
                f"Your monthly disposable income is ${disposable:.0f} "
                f"(base ${p['income']:.0f}" + (f" + UBI ${ubi:.0f}" if ubi > 0 else "") + "). "
                f"Savings: ${env._savings[p['id']]:.0f}. "
                f"How much will you spend this month? Give a dollar amount. "
                f"Also rate your happiness 0-10."
            )

            # Fallback: manual parsing if the agent didn't use the tools directly.
            # The tools (make_consumption_decision, update_happiness) are exposed
            # to the LLM via the CodeGenRouter, but we also parse the text response
            # as a safety net in case the LLM responds with plain text instead.
            amounts = re.findall(r"\$?(\d+(?:,\d{3})*(?:\.\d+)?)", resp)
            if amounts:
                spend = float(amounts[0].replace(",", ""))
                actual = min(spend, disposable + env._savings[p["id"]])
                env._consumption[p["id"]] += actual
                env._savings[p["id"]] = max(0, env._savings[p["id"]] + disposable - spend)

            hap = re.findall(r"(\d+(?:\.\d+)?)\s*/?\s*10", resp)
            if hap:
                env._happiness[p["id"]] = max(0, min(10, float(hap[0])))

        m = env.get_metrics()
        metrics.append({"month": month, **m})

    # Interview about UBI
    interviews = []
    if ubi > 0:
        for p in profiles[:3]:
            resp = await society.ask(
                f"You are {p['name']}. You have been receiving ${ubi}/month in UBI. "
                f"What is your opinion on this policy? How has it affected your life? "
                f"Be specific about spending, savings, and wellbeing."
            )
            interviews.append({"agent": p["name"], "response": resp[:300]})

    await society.close()

    return {
        "metrics": metrics,
        "final": env.get_metrics(),
        "interviews": interviews,
    }
