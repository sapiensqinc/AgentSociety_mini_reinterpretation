"""Chat message display component."""

import streamlit as st


def chat_view(messages: list[dict]):
    for msg in messages:
        role = msg.get("role", "user")
        with st.chat_message(role):
            st.write(msg["content"])


def add_message(role: str, content: str):
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    st.session_state["chat_history"].append({"role": role, "content": content})
