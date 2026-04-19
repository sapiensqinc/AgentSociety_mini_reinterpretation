"""01. Hello Agent — chat with a single PersonAgent."""

import asyncio
import streamlit as st
from app.config import require_api_key
from app.security import ready_to_run, sanitize_user_input, show_safe_error
from app.components.agent_card import agent_card


PROFILE = {
    "name": "Alice",
    "age": 28,
    "personality": "friendly, curious, and optimistic",
    "bio": "A software engineer who loves hiking, reading sci-fi novels, and cooking.",
    "location": "San Francisco",
}

PRESET_QUESTIONS = [
    "What's the name of all agents?",
    "Tell me about Alice's personality and interests.",
    "What agents exist in this simulation?",
]


def render():
    st.header("01. Hello Agent")
    st.caption("Source: paper §3 · code `agentsociety2/agent/person_agent.py` · mini `agentsociety2_lite/agent/`")

    st.info(
        "**Purpose.** 단일 PersonAgent와 대화합니다 — 프로필 기반 시스템 프롬프트가 "
        "어떻게 에이전트의 응답 스타일을 결정하는지 확인하는 가장 작은 예제.\n\n"
        "**Expected result.** Alice는 프로필(28세, 친근, SF 거주, 등산/SF소설)을 "
        "바탕으로 답변하고, 환경에 등록된 에이전트 목록은 도구 호출로 답합니다."
    )

    with st.expander("이 예제에 대하여 — 상세", expanded=False):
        st.markdown("""
**논문 대응**: AgentSociety 논문(arXiv:2502.08691) Section 3 "LLM-driven Social Generative Agents"의 기본 개념을 시연합니다.
논문에서 에이전트는 감정, 욕구, 인지 계층을 가진 복합 존재로 설계되었으며, 이 예제는 그 중 가장 기초적인 형태인
프로필 기반 대화 에이전트를 구현합니다.

**원본 코드 위치**: 원본 GitHub([tsinghua-fib-lab/AgentSociety](https://github.com/tsinghua-fib-lab/AgentSociety))의
`agentsociety2` 패키지에서 `PersonAgent`는 프로필(이름, 나이, 성격, 배경)을 시스템 프롬프트로 변환하여
LLM에 전달하는 가장 기본적인 에이전트 클래스입니다.

**동작 원리**: PersonAgent는 프로필 딕셔너리를 받아 "You are Alice. Your age: 28. Your personality: friendly..."
형태의 시스템 프롬프트를 자동 생성합니다. 사용자의 질문은 CodeGenRouter를 통해 환경 도구(SimpleSocialSpace)와
LLM을 연결하여 처리됩니다. 환경에 등록된 에이전트 목록 조회는 도구 호출로, 성격 같은 프로필 정보는 시스템 프롬프트에서 답합니다.

**해결하는 문제**: LLM 기반 에이전트 시뮬레이션의 진입 장벽을 낮추는 것이 목적입니다.
연구자가 복잡한 인프라 없이도 프로필만 정의하면 즉시 대화 가능한 에이전트를 만들 수 있음을 보여줍니다.
        """)

    with st.expander("Agent Profile", expanded=True):
        agent_card("Alice", PROFILE)

    # Initialize state
    if "hello_history" not in st.session_state:
        st.session_state.hello_history = []
    if "hello_pending" not in st.session_state:
        st.session_state.hello_pending = None

    # Preset question buttons — store in pending, don't process yet
    st.markdown("**시나리오 질문:**")
    cols = st.columns(3)
    for i, q in enumerate(PRESET_QUESTIONS):
        if cols[i].button(q[:30] + "...", key=f"preset_{i}"):
            st.session_state.hello_pending = q
            st.rerun()

    # Display chat history
    for msg in st.session_state.hello_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_input = st.chat_input("Ask Alice a question...")

    # Determine the question to process (pending preset or new input)
    question = None
    if st.session_state.hello_pending:
        question = st.session_state.hello_pending
        st.session_state.hello_pending = None
    elif user_input:
        question = user_input

    if question and ready_to_run(tag="hello_agent"):
        try:
            question = sanitize_user_input(question)
        except ValueError as e:
            st.error(str(e))
            return

        # Display user message
        st.session_state.hello_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Generate and display response
        with st.chat_message("assistant"):
            with st.spinner("Alice is thinking..."):
                try:
                    response = asyncio.run(_ask(question))
                except Exception as e:
                    show_safe_error(e, context="Failed to process request")
                    return
            st.markdown(response)

        st.session_state.hello_history.append({"role": "assistant", "content": response})
        st.rerun()

    if st.button("Clear Chat"):
        st.session_state.hello_history = []
        st.session_state.hello_pending = None
        st.rerun()


async def _ask(question):
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from agentsociety2_lite.contrib import SimpleSocialSpace
    from datetime import datetime

    agent = PersonAgent(id=1, profile=PROFILE)
    social_env = SimpleSocialSpace(agent_id_name_pairs=[(agent.id, agent.name)])
    router = CodeGenRouter(env_modules=[social_env])
    society = AgentSociety(agents=[agent], env_router=router, start_t=datetime.now())
    await society.init()
    response = await society.ask(question)
    await society.close()
    return response
