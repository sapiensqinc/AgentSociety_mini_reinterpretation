"""02. Public Goods Game — multi-player contribution game."""

import asyncio
import re
import streamlit as st
import plotly.graph_objects as go
from app.config import require_api_key
from app.security import ready_to_run, cap, show_safe_error


AGENT_PROFILES = [
    {"name": "Alice", "personality": "altruistic and community-minded"},
    {"name": "Bob", "personality": "self-interested and rational"},
    {"name": "Charlie", "personality": "cautious and skeptical"},
    {"name": "Diana", "personality": "optimistic and trusting"},
]


def render():
    st.header("02. Public Goods Game")
    st.caption("Source: behavioral economics (related to paper §4.4 Economic Space) · main `agentsociety2/contrib/env/public_goods.py` · mini `agentsociety2_lite/contrib/public_goods.py`")

    st.info(
        "**Purpose.** N-agent 공공재 게임 — 각자 기부금을 내면 승수 효과로 증가해 모두에게 "
        "균등 분배. 무임승차(무기여)가 개인에게 유리하지만 모두가 그러면 집단 손실.\n\n"
        "**Expected result.** 초기 라운드는 기여율 50%대, 라운드 진행 시 무임승차 학습으로 "
        "기여율 하락 경향. 이타적 성향 프로필이 많으면 협력 유지."
    )

    with st.expander("이 예제에 대하여 — 상세", expanded=False):
        st.markdown("""
**논문 대응**: 논문 Section 4.4 "Economic Space"에서 다루는 경제적 의사결정의 미시적 버전입니다.
논문에서는 DSGE 기반 거시경제 모델(기업, 정부, 은행, 세금)을 구현했지만,
이 예제는 가장 기본적인 경제 실험인 공공재 게임으로 집단 내 협력 문제를 시연합니다.

**원본 코드 위치**: `agentsociety2/contrib/env/public_goods.py`에 구현되어 있습니다.
원본에는 이 외에도 공유지의 비극(Tragedy of Commons), 신뢰 게임(Trust Game),
자원봉사 딜레마(Volunteer's Dilemma) 등 다양한 경제 실험 환경이 포함되어 있습니다.

**동작 원리**: 4명의 에이전트가 각자 $100을 보유한 상태에서, 공공재에 기여할 금액을 결정합니다.
총 기여금에 1.5배 배수를 곱한 뒤 4명에게 균등 분배합니다. 이 과정을 여러 라운드 반복하면서
에이전트의 성격(이타적/이기적/신중함)이 기여 전략에 어떤 영향을 미치는지 관찰합니다.

**해결하는 문제**: 무임승차 문제(free-rider problem)를 LLM 에이전트로 시뮬레이션합니다.
이기적 에이전트가 적게 내고 많이 받는 구조에서, 이타적 에이전트들이 라운드가 진행됨에 따라
전략을 어떻게 조정하는지, 집단 협력이 유지되는지 또는 붕괴되는지를 관찰할 수 있습니다.
        """)

    col1, col2, col3 = st.columns(3)
    endowment = col1.number_input("Endowment ($)", 10, 1000, 100)
    factor = col2.number_input("Multiplier", 1.0, 5.0, 1.5, 0.1)
    rounds = cap("rounds", col3.number_input("Rounds", 1, 10, 3))

    if st.button("Start Game") and ready_to_run(tag="public_goods"):
        with st.spinner("Running game..."):
            try:
                results = asyncio.run(_run_game(endowment, factor, int(rounds)))
            except Exception as e:
                show_safe_error(e, context="Failed to run game")
                return

        # Show each round
        for rnd in results["rounds"]:
            st.subheader(f"Round {rnd['round']}")

            cols = st.columns(4)
            for i, (name, amount) in enumerate(rnd["contributions"].items()):
                with cols[i]:
                    st.metric(name, f"${amount}")
                    st.progress(amount / endowment)

            st.info(
                f"Total: ${rnd['total']} \u2192 \u00d7{factor} \u2192 "
                f"${rnd['multiplied']} \u2192 ${rnd['each_return']}/person"
            )

        # Contribution trend chart
        st.markdown("---")
        st.subheader("Contribution Trend")
        fig = go.Figure()
        names = list(results["rounds"][0]["contributions"].keys())
        for name in names:
            values = [r["contributions"][name] for r in results["rounds"]]
            fig.add_trace(go.Scatter(
                x=list(range(1, len(results["rounds"]) + 1)),
                y=values, name=name, mode="lines+markers",
            ))
        fig.update_layout(xaxis_title="Round", yaxis_title="Contribution ($)", height=350)
        st.plotly_chart(fig, use_container_width=True)

        # Final reflection
        if results.get("reflection"):
            st.subheader("Final Reflection")
            st.info(results["reflection"])


async def _run_game(endowment, factor, num_rounds):
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from agentsociety2_lite.contrib import PublicGoodsGame
    from datetime import datetime

    game = PublicGoodsGame(endowment=endowment, contribution_factor=factor)
    agents = [PersonAgent(id=i+1, profile=p) for i, p in enumerate(AGENT_PROFILES)]
    router = CodeGenRouter(env_modules=[game])
    society = AgentSociety(agents=agents, env_router=router, start_t=datetime.now())
    await society.init()

    rounds_data = []
    for rnd in range(1, num_rounds + 1):
        contributions = {}
        for agent, profile in zip(agents, AGENT_PROFILES):
            decision = await society.ask(
                f"You are {profile['name']}. You have ${endowment}. "
                f"How much will you contribute to the public good (0-${endowment})? "
                f"The total will be multiplied by {factor} and split among {len(agents)} players."
            )
            match = re.search(r'\$?(\d+)', decision)
            amount = min(max(int(match.group(1)), 0), endowment) if match else endowment // 2
            contributions[profile["name"]] = amount

        total = sum(contributions.values())
        multiplied = int(total * factor)
        each_return = multiplied // len(agents)
        rounds_data.append({
            "round": rnd, "contributions": contributions,
            "total": total, "multiplied": multiplied, "each_return": each_return,
        })

    reflection = await society.ask(
        "The game is over. Reflect on the group's behavior. "
        "Did the group cooperate enough? What could have been done differently?"
    )
    await society.close()

    return {"rounds": rounds_data, "reflection": reflection}
