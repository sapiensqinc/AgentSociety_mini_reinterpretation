"""03. Replay System — record and playback agent interactions."""

import asyncio
import streamlit as st
from pathlib import Path
from app.config import require_api_key


def render():
    st.header("03. Replay System")
    st.caption("Branch: `examples-basics` | \uc2dc\ubbac\ub808\uc774\uc158 \uae30\ub85d \ubc0f \uc7ac\uc0dd")

    if "replay_data" not in st.session_state:
        st.session_state.replay_data = []
        st.session_state.replay_step = 0

    # Record section
    st.subheader("Record Interactions")
    agent_names = ["Agent1 (friendly)", "Agent2 (curious)", "Agent3 (friendly)"]

    if st.button("Run Simulation", disabled=not require_api_key()) and require_api_key():
        with st.spinner("Running agent interactions..."):
            results = asyncio.run(_run_simulation())
            st.session_state.replay_data = results
            st.session_state.replay_step = 0
        st.rerun()

    # Replay section
    if st.session_state.replay_data:
        data = st.session_state.replay_data
        st.markdown("---")
        st.subheader("Replay")

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if st.button("\u23ee First"):
                st.session_state.replay_step = 0
        with col2:
            if st.button("\u25c0 Prev"):
                st.session_state.replay_step = max(0, st.session_state.replay_step - 1)
        with col3:
            st.markdown(f"**{st.session_state.replay_step + 1} / {len(data)}**")
        with col4:
            if st.button("Next \u25b6"):
                st.session_state.replay_step = min(len(data) - 1, st.session_state.replay_step + 1)
        with col5:
            if st.button("Last \u23ed"):
                st.session_state.replay_step = len(data) - 1

        step = st.session_state.replay_step
        step_slider = st.slider("Step", 0, len(data) - 1, step, key="replay_slider")
        if step_slider != step:
            st.session_state.replay_step = step_slider
            step = step_slider

        col_status, col_detail = st.columns([1, 2])

        with col_status:
            st.markdown("**Agent Status**")
            for i, name in enumerate(agent_names):
                status = "active" if i == step else ("done" if i < step else "waiting")
                icon = {"active": "[ON]", "done": "[OK]", "waiting": "[--]"}[status]
                st.write(f"{icon} {name}")

            st.markdown("**Stats**")
            st.metric("Total Steps", len(data))
            st.metric("Agents", len(agent_names))

        with col_detail:
            item = data[step]
            st.markdown(f"**Step {step + 1}**")
            st.markdown(f"**Prompt:** {item['prompt']}")
            st.markdown(f"**Response:**")
            st.info(item["response"][:500])
    else:
        st.info("Click 'Run Simulation' to record agent interactions.")


async def _run_simulation():
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from agentsociety2_lite.contrib import SimpleSocialSpace
    from datetime import datetime

    agents = [
        PersonAgent(id=i, profile={"name": f"Agent{i}", "personality": "friendly" if i % 2 == 0 else "curious"})
        for i in range(1, 4)
    ]
    social_env = SimpleSocialSpace(agent_id_name_pairs=[(a.id, a.name) for a in agents])
    router = CodeGenRouter(env_modules=[social_env])
    society = AgentSociety(agents=agents, env_router=router, start_t=datetime.now())
    await society.init()

    results = []
    for agent in agents:
        prompt = f"Hello {agent._name}! Introduce yourself briefly."
        response = await society.ask(prompt)
        results.append({"agent": agent._name, "prompt": prompt, "response": response})

    await society.close()
    return results
