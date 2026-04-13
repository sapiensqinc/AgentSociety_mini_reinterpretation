"""02. Public Goods Game — multi-player contribution game."""

import asyncio
import re
import streamlit as st
import plotly.graph_objects as go
from app.config import require_api_key


AGENT_PROFILES = [
    {"name": "Alice", "personality": "altruistic and community-minded"},
    {"name": "Bob", "personality": "self-interested and rational"},
    {"name": "Charlie", "personality": "cautious and skeptical"},
    {"name": "Diana", "personality": "optimistic and trusting"},
]


def render():
    st.header("02. Public Goods Game")
    st.caption("Branch: `examples-games` | \uacf5\uacf5\uc7ac \uae30\uc5ec \uac8c\uc784")

    col1, col2, col3 = st.columns(3)
    endowment = col1.number_input("Endowment ($)", 10, 1000, 100)
    factor = col2.number_input("Multiplier", 1.0, 5.0, 1.5, 0.1)
    rounds = col3.number_input("Rounds", 1, 10, 3)

    if st.button("Start Game") and require_api_key():
        with st.spinner("Running game..."):
            results = asyncio.run(_run_game(endowment, factor, int(rounds)))

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
