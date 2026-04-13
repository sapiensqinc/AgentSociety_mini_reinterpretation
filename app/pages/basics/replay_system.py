"""03. Replay System — record and playback agent interactions."""

import asyncio
import streamlit as st
from app.config import require_api_key


def render():
    st.header("03. Replay System")
    st.caption("Branch: `examples-basics` | 시뮬레이션 기록 및 재생")

    if "replay_data" not in st.session_state:
        st.session_state.replay_data = []
    if "replay_step" not in st.session_state:
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
        max_step = len(data) - 1
        st.markdown("---")
        st.subheader("Replay")

        # Navigation buttons with callbacks
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if st.button("First", on_click=_set_step, args=(0,)):
                pass
        with col2:
            if st.button("Prev", on_click=_step_by, args=(-1, max_step)):
                pass
        with col3:
            st.markdown(f"**{st.session_state.replay_step + 1} / {len(data)}**")
        with col4:
            if st.button("Next", on_click=_step_by, args=(1, max_step)):
                pass
        with col5:
            if st.button("Last", on_click=_set_step, args=(max_step,)):
                pass

        # Slider — use on_change to sync back to replay_step
        st.slider(
            "Step", 0, max_step,
            value=st.session_state.replay_step,
            key="replay_slider",
            on_change=_sync_slider,
        )

        step = st.session_state.replay_step

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
            st.markdown("**Response:**")
            st.info(item["response"][:500])
    else:
        st.info("Click 'Run Simulation' to record agent interactions.")


def _set_step(value):
    st.session_state.replay_step = value
    st.session_state.replay_slider = value


def _step_by(delta, max_step):
    new = st.session_state.replay_step + delta
    new = max(0, min(max_step, new))
    st.session_state.replay_step = new
    st.session_state.replay_slider = new


def _sync_slider():
    st.session_state.replay_step = st.session_state.replay_slider


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
