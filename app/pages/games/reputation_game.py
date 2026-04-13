"""03. Reputation Game — indirect reciprocity with social norms."""

import asyncio
import random
import streamlit as st
import plotly.graph_objects as go
from app.config import require_api_key


PERSONALITIES = [
    "rational and cautious", "emotional", "fair-minded",
    "altruistic", "selfish", "vengeful", "optimistic", "pessimistic",
]


def render():
    st.header("03. Reputation Game")
    st.caption("Branch: `examples-games` | \uac04\uc811 \uc0c1\ud638\uc131 + \uc0ac\ud68c \uaddc\ubc94")

    col1, col2, col3 = st.columns(3)
    z = col1.number_input("Population (Z)", 4, 20, 8)
    benefit = col2.number_input("Benefit", 1, 20, 5)
    cost = col3.number_input("Cost", 1, 10, 1)
    norm = st.selectbox("Social Norm", ["stern_judging", "image_score", "simple_standing"])
    steps = st.slider("Simulation Steps", 5, 30, 10)

    if st.button("Run Simulation") and require_api_key():
        with st.spinner(f"Running {steps} steps with {z} agents..."):
            results = asyncio.run(_run_reputation(z, benefit, cost, norm, steps))

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

        st.subheader("Leaderboard")
        sorted_agents = sorted(results["payoffs"].items(), key=lambda x: x[1], reverse=True)
        for rank, (name, payoff) in enumerate(sorted_agents, 1):
            rep = results["reputations"][name]
            icon = "\ud83d\udfe2" if rep == "good" else "\ud83d\udd34"
            st.write(f"{rank}. {icon} **{name}**: payoff = {payoff:.1f}")

        with st.expander("Recent Interactions"):
            for log in results["logs"][-10:]:
                st.text(log)


async def _run_reputation(z, benefit, cost, norm, steps):
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from agentsociety2_lite.contrib import SimpleSocialSpace
    from datetime import datetime

    random.seed(42)
    agents = []
    for i in range(z):
        personality = random.choice(PERSONALITIES)
        agents.append(PersonAgent(
            id=i, profile={"name": f"Agent{i}", "personality": personality}
        ))

    env = SimpleSocialSpace(agent_id_name_pairs=[(a.id, a.name) for a in agents])
    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=agents, env_router=router, start_t=datetime.now())
    await society.init()

    reputations = {f"Agent{i}": "good" for i in range(z)}
    payoffs = {f"Agent{i}": 0.0 for i in range(z)}
    coop_history = []
    logs = []

    for step in range(steps):
        # Random donor-recipient pair
        ids = list(range(z))
        random.shuffle(ids)
        donor_id, recip_id = ids[0], ids[1]
        donor_name = f"Agent{donor_id}"
        recip_name = f"Agent{recip_id}"
        recip_rep = reputations[recip_name]

        decision = await society.ask(
            f"You are {donor_name}. You meet {recip_name} whose reputation is {recip_rep}. "
            f"If you COOPERATE, you pay {cost} and they gain {benefit}. "
            f"If you DEFECT, nothing happens. Choose COOPERATE or DEFECT."
        )
        cooperated = "cooperate" in decision.lower()

        if cooperated:
            payoffs[donor_name] -= cost
            payoffs[recip_name] += benefit

        # Update reputation based on norm
        if norm == "stern_judging":
            if cooperated and recip_rep == "good":
                reputations[donor_name] = "good"
            elif cooperated and recip_rep == "bad":
                reputations[donor_name] = "bad"
            elif not cooperated and recip_rep == "good":
                reputations[donor_name] = "bad"
            else:
                reputations[donor_name] = "good"
        elif norm == "image_score":
            reputations[donor_name] = "good" if cooperated else "bad"
        else:  # simple_standing
            if cooperated:
                reputations[donor_name] = "good"
            elif recip_rep == "good":
                reputations[donor_name] = "bad"

        action = "COOPERATE" if cooperated else "DEFECT"
        logs.append(f"Step {step+1}: {donor_name}({reputations[donor_name][0].upper()}) -> "
                    f"{recip_name}({recip_rep[0].upper()}): {action}")

        good_count = sum(1 for r in reputations.values() if r == "good")
        coop_history.append(good_count / z)

    await society.close()
    return {
        "reputations": reputations, "payoffs": payoffs,
        "coop_history": coop_history, "logs": logs,
    }
