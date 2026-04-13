"""01. Prisoner's Dilemma — two agents choose cooperate/defect."""

import asyncio
import streamlit as st
import plotly.graph_objects as go
from app.config import require_api_key


def render():
    st.header("01. Prisoner's Dilemma")
    st.caption("Branch: `examples-games` | \uace0\uc804 \uac8c\uc784\uc774\ub860 \uc2dc\ub098\ub9ac\uc624")

    col_setup, col_matrix = st.columns([1, 1])

    with col_setup:
        st.subheader("Game Setup")
        c_reward = st.number_input("Cooperate Reward (years)", 0, 10, 1)
        d_punish = st.number_input("Defect Punishment (years)", 0, 10, 1)
        tempt = st.number_input("Temptation", 0, 10, 3)
        sucker = st.number_input("Sucker Punishment", 0, 10, 3)

    with col_matrix:
        st.subheader("Payoff Matrix")
        cc = c_reward
        dd = c_reward + d_punish + 1
        cd_c = c_reward + sucker + 1
        cd_d = 0

        fig = go.Figure(data=[go.Table(
            header=dict(values=["", "Bob: Cooperate", "Bob: Defect"],
                       fill_color="#264653", font=dict(color="white")),
            cells=dict(values=[
                ["Alice: Cooperate", "Alice: Defect"],
                [f"{cc}, {cc}", f"{cd_d}, {cd_c}"],
                [f"{cd_c}, {cd_d}", f"{dd}, {dd}"],
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
    alice = PersonAgent(id=1, profile={"name": "Alice", "personality": "strategic and rational"})
    bob = PersonAgent(id=2, profile={"name": "Bob", "personality": "trusting but cautious"})
    router = CodeGenRouter(env_modules=[game])
    society = AgentSociety(agents=[alice, bob], env_router=router, start_t=datetime.now())
    await society.init()

    alice_resp = await society.ask(
        "You are Alice in a prisoner's dilemma. Choose COOPERATE or DEFECT. Explain your reasoning."
    )
    bob_resp = await society.ask(
        "You are Bob in a prisoner's dilemma. Choose COOPERATE or DEFECT. Explain your reasoning."
    )

    alice_coop = "cooperate" in alice_resp.lower()
    bob_coop = "cooperate" in bob_resp.lower()

    if alice_coop and bob_coop:
        a_s, b_s, outcome = c_reward, c_reward, "Both COOPERATED"
    elif alice_coop:
        a_s, b_s, outcome = c_reward + sucker + 1, 0, "Alice COOPERATED, Bob DEFECTED"
    elif bob_coop:
        a_s, b_s, outcome = 0, c_reward + sucker + 1, "Alice DEFECTED, Bob COOPERATED"
    else:
        a_s, b_s, outcome = c_reward + d_punish + 1, c_reward + d_punish + 1, "Both DEFECTED"

    reflection = await society.ask(
        f"Results: {outcome}. Alice got {a_s} years, Bob got {b_s} years. "
        f"Are you satisfied? Would you make the same choice?"
    )
    await society.close()

    return {
        "alice_cooperates": alice_coop, "bob_cooperates": bob_coop,
        "alice_reasoning": alice_resp, "bob_reasoning": bob_resp,
        "alice_sentence": a_s, "bob_sentence": b_s,
        "outcome": outcome, "reflection": reflection,
    }
