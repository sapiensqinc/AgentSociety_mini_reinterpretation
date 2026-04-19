"""Paper: UBI Experiment (Section 7.4).

Paper fidelity (§7.4):
- Texas demographics, w/UBI vs w/o UBI comparison
- UBI introduced at simulation step 96 (1 step = 1 month), follow-up 24 months
- Depression measured via CES-D 20-item scale (Radloff 1977)
- Metrics: consumption level, depression level
- Result: UBI increases consumption and reduces depression

Implementation notes:
- CES-D 20 items each rated 0-3 (rarely / some / occasionally / most)
- Items 4, 8, 12, 16 are reverse-scored (positive affect)
- Total score range 0-60; clinical cutoff ~16
- A faithful 96-month run is expensive; the UI exposes `ubi_start_month` and
  `followup_months` so researchers can reproduce the paper structure at any scale.
"""

import asyncio
import json
import re
import random
from typing import Dict, List

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.config import require_api_key
from app.security import (
    ready_to_run, cap, show_safe_error,
    sanitize_user_input, spotlight, sanitize_llm_output,
)
from agentsociety2_lite.env import EnvBase, tool


OCCUPATIONS = ["retail worker", "teacher", "nurse", "truck driver",
               "software engineer", "construction worker", "cashier", "waiter"]

DESCRIPTION = """
**논문 대응**: 논문 Section 7.4 "Universal Basic Income"을 재현한 실험입니다.
논문에서는 텍사스주 주민 프로필 기반으로 월 $1,000 UBI 지급 시나리오를 시뮬레이션하여,
소비 수준과 우울증 수준(CES-D 척도) 변화를 UBI 미지급 조건과 비교했습니다.
논문에서는 UBI를 step 96에 도입하고 24 step 이후까지 관찰하였습니다 (1 step = 1 month).

**논문 결과**: UBI 지급 시 소비 수준이 증가하고 우울증(CES-D) 수준이 감소했습니다.
에이전트 인터뷰에서는 금리에 대한 우려, 장기적 혜택에 대한 기대, 저축 습관 변화 등
현실적인 반응이 관찰되었습니다.

**이 구현의 충실도**:
- CES-D 20-item 우울증 척도 구현 (옵션 토글) — 논문의 "depression" 메트릭과 직접 대응
- `UBI 도입 월 (step)`과 `관찰 기간 (months)` 슬라이더 — 논문의 step-96 + 24-month 구조를 축소된 스케일로 재현
- 소비 / 저축 / 행복도 시계열 추적
"""


# ---- CES-D 20-item Depression Scale (Radloff 1977) ----
# Each item rated 0-3: (0) Rarely / <1 day  (1) Some / 1-2 days
#                      (2) Occasionally / 3-4 days  (3) Most / 5-7 days
CESD_ITEMS = [
    "I was bothered by things that usually don't bother me.",
    "I did not feel like eating; my appetite was poor.",
    "I felt that I could not shake off the blues even with help from my family or friends.",
    "I felt that I was just as good as other people.",                    # reverse
    "I had trouble keeping my mind on what I was doing.",
    "I felt depressed.",
    "I felt that everything I did was an effort.",
    "I felt hopeful about the future.",                                   # reverse
    "I thought my life had been a failure.",
    "I felt fearful.",
    "My sleep was restless.",
    "I was happy.",                                                        # reverse
    "I talked less than usual.",
    "I felt lonely.",
    "People were unfriendly.",
    "I enjoyed life.",                                                     # reverse
    "I had crying spells.",
    "I felt sad.",
    "I felt that people disliked me.",
    "I could not get \"going.\"",
]
CESD_REVERSE = {4, 8, 12, 16}  # 1-indexed items that are reverse scored


def _cesd_prompt(agent_name: str, past_month_ctx: str) -> str:
    """Build the CES-D rating prompt for a single agent.

    The agent is told the rating scale and asked for all 20 ratings at once
    as a JSON array to keep cost to one call per agent per measurement.
    """
    items_block = "\n".join(f"{i+1}. {txt}" for i, txt in enumerate(CESD_ITEMS))
    return (
        f"You are {agent_name}. Think back over the past month given this context:\n"
        f"{past_month_ctx}\n\n"
        "Rate how often you felt each of the following (0-3):\n"
        "  0 = Rarely or none of the time (less than 1 day)\n"
        "  1 = Some or a little (1-2 days)\n"
        "  2 = Occasionally or a moderate amount (3-4 days)\n"
        "  3 = Most or all of the time (5-7 days)\n\n"
        f"{items_block}\n\n"
        "Respond ONLY with a JSON object of the form "
        '{"ratings": [r1, r2, ..., r20]} where each r is 0, 1, 2 or 3.'
    )


def _parse_cesd(text: str) -> int | None:
    """Parse agent response and return a CES-D score (0-60).

    Accepts either a JSON object with key "ratings" or a bare JSON list of 20
    integers. Applies reverse scoring for items 4, 8, 12, 16.
    Returns None if parsing fails or list length is wrong.
    """
    if not text:
        return None
    # Try JSON object first
    m = re.search(r"\{[^{}]*\"ratings\"\s*:\s*\[[^\]]*\][^{}]*\}", text, re.DOTALL)
    ratings: list | None = None
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict) and isinstance(obj.get("ratings"), list):
                ratings = obj["ratings"]
        except json.JSONDecodeError:
            ratings = None
    if ratings is None:
        # Fallback: any bare list of 20 ints
        m2 = re.search(r"\[\s*(?:\d+\s*,\s*){19}\d+\s*\]", text)
        if m2:
            try:
                ratings = json.loads(m2.group(0))
            except json.JSONDecodeError:
                ratings = None
    if not isinstance(ratings, list) or len(ratings) != 20:
        return None
    total = 0
    for i, r in enumerate(ratings, start=1):
        try:
            r = int(r)
        except (TypeError, ValueError):
            return None
        r = max(0, min(3, r))
        if i in CESD_REVERSE:
            r = 3 - r
        total += r
    return total


class EconomyEnv(EnvBase):
    """Simplified economic environment for UBI experiment.

    `ubi_amount` is mutable at runtime so the monthly loop can introduce UBI
    at step N (matching the paper's step-96 structure).
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

    def set_ubi(self, amount: float) -> None:
        self._ubi = amount

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
        st.markdown(DESCRIPTION)

    col_a, col_b, col_c = st.columns(3)
    n_agents = cap("agents", col_a.number_input("Agents", 4, 16, 8))
    ubi_amount = col_b.number_input("UBI Amount ($/month)", 0, 5000, 1000, 100)
    total_months = cap("rounds", col_c.number_input("Total months", 1, 12, 6))

    col_d, col_e = st.columns(2)
    ubi_start_month = col_d.number_input(
        "UBI 도입 시점 (month)",
        min_value=0, max_value=max(0, total_months - 1), value=0,
        help="논문은 step 96에 도입. 0이면 처음부터 UBI 지급(요약 비교용).",
    )
    run_cesd = col_e.checkbox(
        "CES-D 우울증 평가 실행 (+1 LLM 호출/에이전트/조건)",
        value=False,
        help="논문의 depression 메트릭을 충실 재현. 비용이 약 2배가 됨.",
    )

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
                r_no = asyncio.run(_run_ubi(profiles, 0, total_months, 0, run_cesd))
            except Exception as e:
                show_safe_error(e, context="Failed to run No UBI condition")
                return
        with st.spinner(f"Running UBI condition (introduce at month {ubi_start_month})..."):
            try:
                r_yes = asyncio.run(_run_ubi(profiles, ubi_amount, total_months, ubi_start_month, run_cesd))
            except Exception as e:
                show_safe_error(e, context="Failed to run UBI condition")
                return

        st.markdown("---")

        # Time-series charts
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
        if ubi_start_month > 0:
            fig.add_vline(
                x=ubi_start_month, line_dash="dot", line_color="gray",
                annotation_text="UBI intro", annotation_position="top",
            )
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

        # CES-D comparison (paper Fig 20b)
        if run_cesd and r_no.get("cesd_mean") is not None and r_yes.get("cesd_mean") is not None:
            st.subheader("CES-D Depression Level (Paper Fig 20b)")
            d_no = r_no["cesd_mean"]; d_yes = r_yes["cesd_mean"]
            cesd_fig = go.Figure(data=[
                go.Bar(name="No UBI", x=["CES-D"], y=[d_no], marker_color="#e74c3c"),
                go.Bar(name=f"UBI ${ubi_amount}", x=["CES-D"], y=[d_yes], marker_color="#2ecc71"),
            ])
            cesd_fig.update_layout(
                yaxis_title="CES-D score (0-60, higher = more depressed)",
                height=300, yaxis_range=[0, 60],
            )
            st.plotly_chart(cesd_fig, use_container_width=True)
            cold_a, cold_b = st.columns(2)
            cold_a.metric("CES-D (No UBI)", f"{d_no:.1f}")
            cold_b.metric("CES-D (UBI)", f"{d_yes:.1f}", f"{d_yes - d_no:+.1f}")
            st.caption("논문 Fig 20b: UBI 조건에서 CES-D 점수가 소폭 감소하는 경향.")

        # Interviews
        if r_yes.get("interviews"):
            st.subheader("Agent Interviews (UBI condition)")
            for iv in r_yes["interviews"]:
                with st.chat_message("assistant"):
                    st.markdown(f"**{iv['agent']}:**")
                    st.write(sanitize_llm_output(iv["response"])[:300])

        st.caption("Paper: UBI increases consumption, reduces depression")


async def _run_ubi(profiles, ubi, num_months, ubi_start_month, run_cesd):
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from datetime import datetime

    env = EconomyEnv(agent_profiles=profiles, ubi_amount=0 if ubi_start_month > 0 else ubi)
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
        # Paper §7.4: introduce UBI at step ubi_start_month.
        active_ubi = ubi if month > ubi_start_month else 0
        env.set_ubi(active_ubi)

        for p in profiles:
            disposable = p["income"] + active_ubi
            resp = await society.ask(
                f"You are {p['name']}, a {p['occupation']}. "
                f"Your monthly disposable income is ${disposable:.0f} "
                f"(base ${p['income']:.0f}" + (f" + UBI ${active_ubi:.0f}" if active_ubi > 0 else "") + "). "
                f"Savings: ${env._savings[p['id']]:.0f}. "
                f"How much will you spend this month? Give a dollar amount. "
                f"Also rate your happiness 0-10."
            )

            # Fallback parsing if the LLM used plain text instead of the tools.
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

    # CES-D 20-item measurement at end of simulation — paper Fig 20b
    cesd_scores: list[int] = []
    if run_cesd:
        for p in profiles:
            ubi_ctx = (
                f"You have been receiving ${ubi:.0f}/month in UBI "
                f"since month {ubi_start_month + 1}." if ubi > 0
                else "You have not received any UBI payments."
            )
            ctx = (
                f"You are {p['name']}, a {p['occupation']} with monthly income ${p['income']:.0f}. "
                f"{ubi_ctx} "
                f"Current savings: ${env._savings[p['id']]:.0f}, "
                f"total consumption this period: ${env._consumption[p['id']]:.0f}."
            )
            prompt = _cesd_prompt(p["name"], ctx)
            resp = await society.ask(spotlight(sanitize_user_input(prompt, max_len=4000)))
            score = _parse_cesd(resp)
            if score is not None:
                cesd_scores.append(score)

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
        "cesd_scores": cesd_scores,
        "cesd_mean": (sum(cesd_scores) / len(cesd_scores)) if cesd_scores else None,
    }
