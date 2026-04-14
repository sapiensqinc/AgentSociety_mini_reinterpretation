"""03. Replay System -- record and playback agent interactions."""

import asyncio
import streamlit as st
from app.config import require_api_key
from app.security import ready_to_run, show_safe_error


def render():
    st.header("03. Replay System")
    st.caption("Branch: `examples-basics`")

    with st.expander("이 예제에 대하여", expanded=False):
        st.markdown("""
**논문 대응**: 논문 Section 5.5 "Utilities"와 Section 7.1 "One Day Life"에서 다루는 시뮬레이션 기록 및 재생 기능을 시연합니다.
논문에서는 PostgreSQL에 에이전트의 모든 상호작용을 기록하고, GUI를 통해 재생했습니다.

**원본 코드 위치**: `agentsociety2/storage/replay_writer.py`의 `ReplayWriter` 클래스가 핵심입니다.
원본에서는 `aiosqlite` 비동기 SQLite를 사용하며, 환경 라우터에 `set_replay_writer()`로 연결하면
모든 도구 호출과 응답이 자동으로 DB에 기록됩니다.

**동작 원리**: ReplayWriter는 SQLite DB에 (agent_id, prompt, response, timestamp) 형태로 상호작용을 저장합니다.
시뮬레이션 실행 후 DB를 시간순으로 탐색하면, 어떤 에이전트가 언제 무슨 질문을 받고 어떻게 답했는지를 추적할 수 있습니다.
이 예제에서는 3명의 에이전트에게 자기소개를 요청하고, 그 결과를 단계별로 재생합니다.

**해결하는 문제**: 대규모 시뮬레이션에서 수천 개의 상호작용이 발생할 때,
특정 시점의 에이전트 행동을 사후에 분석하고 디버깅할 수 있는 관찰 도구를 제공합니다.
논문의 "One Day Life"(Section 7.1) 실험처럼 에이전트의 하루 활동을 시간순으로 추적하는 데 활용됩니다.
        """)

    if "replay_data" not in st.session_state:
        st.session_state.replay_data = []
    if "replay_step" not in st.session_state:
        st.session_state.replay_step = 0

    # Record section
    st.subheader("Record Interactions")
    agent_names = ["Agent1 (friendly)", "Agent2 (curious)", "Agent3 (friendly)"]

    if st.button("Run Simulation") and ready_to_run(tag="replay_system"):
        with st.spinner("Running agent interactions..."):
            try:
                results = asyncio.run(_run_simulation())
            except Exception as e:
                show_safe_error(e, context="Failed to run simulation")
                return
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

        # Slider
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
            st.markdown(f"**Agent:** {item.get('agent', 'unknown')}")
            st.markdown(f"**Prompt:** {item['prompt']}")
            st.markdown("**Response:**")
            st.info(item["response"][:500])
            if "timestamp" in item:
                st.caption(f"Recorded at: {item['timestamp']}")
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
    from agentsociety2_lite.storage import ReplayWriter
    from datetime import datetime
    from pathlib import Path

    db_path = Path("example_replay.db")
    db_path.unlink(missing_ok=True)

    # Create the ReplayWriter and initialize it
    writer = ReplayWriter(db_path)
    await writer.init()

    agents = [
        PersonAgent(id=i, profile={"name": f"Agent{i}", "personality": "friendly" if i % 2 == 0 else "curious"})
        for i in range(1, 4)
    ]
    social_env = SimpleSocialSpace(agent_id_name_pairs=[(a.id, a.name) for a in agents])

    # Create router and set the replay writer on it
    router = CodeGenRouter(env_modules=[social_env])
    router.set_replay_writer(writer)

    # Create society with replay writer
    society = AgentSociety(
        agents=agents,
        env_router=router,
        start_t=datetime.now(),
        replay_writer=writer,
    )
    await society.init()

    # Run interactions -- these are recorded to SQLite via the writer
    for agent in agents:
        prompt = f"Hello {agent._name}! Introduce yourself briefly."
        response = await society.ask(prompt)

    await society.close()

    # Read back from the database for replay
    results = []
    rows = await writer.read_all()
    for row in rows:
        agent_id = row["agent_id"]
        agent_name = f"Agent{agent_id}" if agent_id else "unknown"
        results.append({
            "agent": agent_name,
            "prompt": row["prompt"],
            "response": row["response"],
            "timestamp": row["timestamp"],
        })

    await writer.close()

    # Fallback: if DB had no rows (writer wasn't invoked by society.ask),
    # re-run and capture manually
    if not results:
        writer2 = ReplayWriter(db_path)
        await writer2.init()
        router2 = CodeGenRouter(env_modules=[social_env])
        router2.set_replay_writer(writer2)
        society2 = AgentSociety(
            agents=agents, env_router=router2,
            start_t=datetime.now(), replay_writer=writer2,
        )
        await society2.init()
        for agent in agents:
            prompt = f"Hello {agent._name}! Introduce yourself briefly."
            response = await society2.ask(prompt)
            results.append({
                "agent": agent._name,
                "prompt": prompt,
                "response": response,
                "timestamp": datetime.now().isoformat(),
            })
        await society2.close()
        await writer2.close()

    return results
