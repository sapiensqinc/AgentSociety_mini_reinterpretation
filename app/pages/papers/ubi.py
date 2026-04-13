"""Paper: UBI Experiment (Section 7.4)."""

import asyncio
import re
import random
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from app.config import require_api_key
from agentsociety2_lite.env import EnvBase, tool


OCCUPATIONS = ["retail worker", "teacher", "nurse", "truck driver",
               "software engineer", "construction worker", "cashier", "waiter"]


def _generate_profiles(n=8, seed=42):
    random.seed(seed)
    return [{
        "id": i + 1, "name": f"Resident_{i+1}",
        "occupation": OCCUPATIONS[i % len(OCCUPATIONS)],
        "income": round(max(1200, min(8000, random.gauss(3500, 1500)))),
        "savings": round(random.uniform(1000, 15000)),
        "happiness": round(random.uniform(3, 7), 1),
    } for i in range(n)]


def render():
    st.header("UBI Experiment (Paper Sec 7.4)")
    st.caption("Branch: `paper-ubi`")

    with st.expander("이 예제에 대하여", expanded=False):
        st.markdown("""
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
        """)

    n_agents = st.number_input("Agents", 4, 16, 8)
    ubi_amount = st.number_input("UBI Amount ($/month)", 0, 5000, 1000, 100)
    months = st.number_input("Months", 1, 6, 3)

    profiles = _generate_profiles(n_agents)

    with st.expander("Agent Profiles"):
        st.dataframe([{
            "Name": p["name"], "Occupation": p["occupation"],
            "Income": f"${p['income']}", "Savings": f"${p['savings']}",
            "Happiness": p["happiness"],
        } for p in profiles])

    if st.button("Run Experiment") and require_api_key():
        with st.spinner("Running No UBI condition..."):
            r_no = asyncio.run(_run_ubi(profiles, 0, months))
        with st.spinner("Running UBI condition..."):
            r_yes = asyncio.run(_run_ubi(profiles, ubi_amount, months))

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
    from agentsociety2_lite.env import EnvBase, tool
    from datetime import datetime

    env = EconomyEnv(profiles, ubi)
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
                f"Disposable income: ${disposable} "
                f"(base ${p['income']}" + (f" + UBI ${ubi}" if ubi > 0 else "") + "). "
                f"Savings: ${env._savings[p['id']]:.0f}. "
                f"How much will you spend? Give a dollar amount. Rate happiness 0-10."
            )

            amounts = re.findall(r"\$?(\d+(?:,\d{3})*(?:\.\d+)?)", resp)
            if amounts:
                spend = float(amounts[0].replace(",", ""))
                env._consumption[p["id"]] += min(spend, disposable + env._savings[p["id"]])
                env._savings[p["id"]] = max(0, env._savings[p["id"]] + disposable - spend)

            hap = re.findall(r"(\d+(?:\.\d+)?)\s*/?\s*10", resp)
            if hap:
                env._happiness[p["id"]] = max(0, min(10, float(hap[0])))

        n = len(profiles)
        metrics.append({
            "month": month,
            "avg_consumption": sum(env._consumption.values()) / n,
            "avg_savings": sum(env._savings.values()) / n,
            "avg_happiness": sum(env._happiness.values()) / n,
        })

    interviews = []
    if ubi > 0:
        for p in profiles[:3]:
            resp = await society.ask(
                f"You are {p['name']}. You receive ${ubi}/month in UBI. "
                f"What is your opinion? How has it affected your life?"
            )
            interviews.append({"agent": p["name"], "response": resp})

    await society.close()

    n = len(profiles)
    return {
        "metrics": metrics,
        "final": {
            "avg_consumption": sum(env._consumption.values()) / n,
            "avg_savings": sum(env._savings.values()) / n,
            "avg_happiness": sum(env._happiness.values()) / n,
        },
        "interviews": interviews,
    }


class EconomyEnv(EnvBase):
    def __init__(self, profiles, ubi):
        super().__init__()
        self._savings = {p["id"]: p["savings"] for p in profiles}
        self._consumption = {p["id"]: 0.0 for p in profiles}
        self._happiness = {p["id"]: p["happiness"] for p in profiles}
        self._ubi = ubi

    @tool(readonly=True, kind="statistics")
    def get_economy_stats(self) -> str:
        """Get aggregate economic statistics."""
        n = len(self._savings)
        return (f"Avg consumption: ${sum(self._consumption.values())/n:.0f}, "
                f"Avg savings: ${sum(self._savings.values())/n:.0f}, "
                f"Avg happiness: {sum(self._happiness.values())/n:.1f}")
