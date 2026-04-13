"""01. Hello Agent — chat with a single PersonAgent."""

import asyncio
import streamlit as st
from app.config import require_api_key
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
    st.caption("Branch: `examples-basics` | 기본 에이전트 대화 예제")

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

    if question and require_api_key():
        # Display user message
        st.session_state.hello_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Generate and display response
        with st.chat_message("assistant"):
            with st.spinner("Alice is thinking..."):
                response = asyncio.run(_ask(question))
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
