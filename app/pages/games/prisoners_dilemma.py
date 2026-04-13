"""01. Prisoner's Dilemma -- two agents choose cooperate/defect."""

import asyncio
import streamlit as st
import plotly.graph_objects as go
from app.config import require_api_key


def render():
    st.header("01. Prisoner's Dilemma")
    st.caption("Branch: `examples-games`")

    with st.expander("이 예제에 대하여", expanded=False):
        st.markdown("""
**논문 대응**: 논문 본문에는 게임이론 실험이 포함되어 있지 않습니다. 이 모듈은 v2 코드에서
새로 추가된 `agentsociety2/contrib/env/` 디렉토리의 게임이론 환경 중 하나입니다.
논문 Section 3.4 "Social Behaviors"에서 에이전트 간 상호작용의 기초가 되는
협력/배신 의사결정 메커니즘을 가장 단순한 형태로 시연합니다.

**원본 코드 위치**: `agentsociety2/contrib/env/prisoners_dilemma.py`에 `PrisonersDilemma` 환경이 구현되어 있습니다.
원본에서는 보수 매트릭스를 `@tool`로 제공하여 LLM 에이전트가 게임 규칙을 이해한 뒤 전략적으로 결정하도록 합니다.

**동작 원리**: 두 에이전트(Alice, Bob)에게 각각 독립적으로 "COOPERATE 또는 DEFECT를 선택하라"고 질의합니다.
에이전트는 자신의 성격 프로필(strategic/trusting)과 게임 규칙을 고려하여 결정하고, 그 근거를 설명합니다.
두 결정이 모인 뒤 보수 매트릭스에 따라 결과가 계산되고, 에이전트에게 결과를 알려주어 회고하게 합니다.

**해결하는 문제**: LLM 에이전트가 전략적 상황에서 어떻게 추론하는지를 관찰합니다.
내쉬 균형(둘 다 배신)과 파레토 최적(둘 다 협력)의 괴리를 LLM이 인식하는지,
에이전트의 성격이 실제로 결정에 영향을 미치는지를 실험할 수 있습니다.
        """)

    col_setup, col_matrix = st.columns([1, 1])

    with col_setup:
        st.subheader("Game Setup")
        c_reward = st.number_input("Cooperate Reward (both cooperate, years)", 0, 10, 1)
        d_punish = st.number_input("Defect Punishment (both defect, years)", 0, 10, 3)
        tempt = st.number_input("Temptation (defector goes free, years)", 0, 10, 0)
        sucker = st.number_input("Sucker Punishment (cooperator gets, years)", 0, 10, 5)

    with col_matrix:
        st.subheader("Payoff Matrix (years in prison)")
        # Standard game theory payoff matrix:
        # Both cooperate: cooperate_reward each
        # Both defect: defect_punishment each
        # One cooperates, one defects: cooperator=sucker, defector=tempt
        cc = c_reward
        dd = d_punish
        cd_cooperator = sucker
        cd_defector = tempt

        fig = go.Figure(data=[go.Table(
            header=dict(values=["", "Bob: Cooperate", "Bob: Defect"],
                       fill_color="#264653", font=dict(color="white")),
            cells=dict(values=[
                ["Alice: Cooperate", "Alice: Defect"],
                [f"{cc}, {cc}", f"{cd_defector}, {cd_cooperator}"],
                [f"{cd_cooperator}, {cd_defector}", f"{dd}, {dd}"],
            ], fill_color=[["#f0f0f0"]*2, ["#e8f5e9"]*2, ["#ffebee"]*2]),
        )])
        fig.update_layout(height=200, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    if st.button("Run Game") and require_api_key():
        with st.spinner("Agents are deciding..."):
            result = asyncio.run(_run_game(c_reward, d_punish, tempt, sucker))

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Alice")
            st.caption("strategic and rational")
            decision = "COOPERATE" if result["alice_cooperates"] else "DEFECT"
            if result["alice_cooperates"]:
                st.success(f"Decision: {decision}")
            else:
                st.error(f"Decision: {decision}")
            with st.expander("Reasoning"):
                st.write(result["alice_reasoning"])
            st.metric("Sentence", f"{result['alice_sentence']} years")

        with col_b:
            st.subheader("Bob")
            st.caption("trusting but cautious")
            decision = "COOPERATE" if result["bob_cooperates"] else "DEFECT"
            if result["bob_cooperates"]:
                st.success(f"Decision: {decision}")
            else:
                st.error(f"Decision: {decision}")
            with st.expander("Reasoning"):
                st.write(result["bob_reasoning"])
            st.metric("Sentence", f"{result['bob_sentence']} years")

        st.markdown("---")
        st.subheader(f"Result: {result['outcome']}")
        st.info(result["reflection"])


async def _run_game(c_reward, d_punish, tempt, sucker):
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from agentsociety2_lite.contrib import PrisonersDilemma
    from datetime import datetime

    game = PrisonersDilemma(c_reward, d_punish, tempt, sucker)

    alice = PersonAgent(id=1, profile={
        "name": "Alice",
        "personality": "strategic and rational",
        "strategy": "will analyze the situation carefully before deciding",
    })
    bob = PersonAgent(id=2, profile={
        "name": "Bob",
        "personality": "trusting but cautious",
        "strategy": "prefers cooperation but wary of betrayal",
    })

    router = CodeGenRouter(env_modules=[game])
    society = AgentSociety(agents=[alice, bob], env_router=router, start_t=datetime.now())
    await society.init()

    # Detailed scenario prompt matching the original's narrative style
    scenario = (
        "You have been arrested along with another suspect and are being held in separate rooms. "
        "The police are interrogating you both separately. You cannot communicate with each other. "
        "You must choose to either COOPERATE (stay silent) or DEFECT (betray your partner).\n\n"
        "Here are the possible outcomes:\n"
        f"- If BOTH of you COOPERATE (stay silent): You each get {c_reward} year(s) in prison.\n"
        f"- If BOTH of you DEFECT (betray each other): You each get {d_punish} year(s) in prison.\n"
        f"- If YOU COOPERATE but your partner DEFECTS: You get {sucker} year(s) (the 'sucker' penalty) "
        f"and your partner goes free ({tempt} years).\n"
        f"- If YOU DEFECT but your partner COOPERATES: You go free ({tempt} years) "
        f"and your partner gets {sucker} year(s).\n\n"
        "What is your decision? Respond with either 'COOPERATE' or 'DEFECT' and explain your reasoning."
    )

    alice_resp = await society.ask(
        f"You are Alice. {scenario}"
    )
    bob_resp = await society.ask(
        f"You are Bob. {scenario}"
    )

    alice_coop = "cooperate" in alice_resp.lower()
    bob_coop = "cooperate" in bob_resp.lower()

    # Standard game theory payoffs
    if alice_coop and bob_coop:
        a_s, b_s, outcome = c_reward, c_reward, "Both COOPERATED"
    elif alice_coop and not bob_coop:
        a_s, b_s, outcome = sucker, tempt, "Alice COOPERATED, Bob DEFECTED"
    elif not alice_coop and bob_coop:
        a_s, b_s, outcome = tempt, sucker, "Alice DEFECTED, Bob COOPERATED"
    else:
        a_s, b_s, outcome = d_punish, d_punish, "Both DEFECTED"

    reflection = await society.ask(
        f"The results are in: {outcome}. Alice got {a_s} year(s), Bob got {b_s} year(s). "
        f"Are you satisfied with your decision? Would you make the same choice again? "
        f"Explain your thinking."
    )
    await society.close()

    return {
        "alice_cooperates": alice_coop, "bob_cooperates": bob_coop,
        "alice_reasoning": alice_resp, "bob_reasoning": bob_resp,
        "alice_sentence": a_s, "bob_sentence": b_s,
        "outcome": outcome, "reflection": reflection,
    }
