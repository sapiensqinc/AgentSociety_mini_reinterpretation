"""Reusable agent profile card component."""

import streamlit as st


def agent_card(name: str, profile: dict, container=None):
    fields = []
    for k, v in profile.items():
        if k == "name":
            continue
        if isinstance(v, dict):
            for sk, sv in v.items():
                fields.append(f"**{sk}**: {sv}")
        else:
            fields.append(f"**{k}**: {v}")
    body = "  \n".join(fields)

    if container is not None:
        with container:
            st.info(f"**{name}**  \n{body}")
    else:
        st.info(f"**{name}**  \n{body}")


def agent_cards_row(agents: list[dict]):
    cols = st.columns(len(agents))
    for col, agent in zip(cols, agents):
        agent_card(agent.get("name", "Agent"), agent, container=col)
