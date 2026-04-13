"""02. Multi-Router Comparison — compare ReAct, PlanExecute, CodeGen."""

import asyncio
import time
import streamlit as st
import plotly.graph_objects as go
from app.config import require_api_key


PRESETS = {
    "Apple Math": ("I have 10 apples. I give 3 to Alice and 2 to Bob. "
                   "Then Alice gives me back 1 apple. How many apples do I have now? "
                   "Show your work step by step."),
    "Auction Simulation": ("Simulate a small auction where 3 people bid on an item. "
                           "Start at $10, increment by $5, and stop after 3 rounds. "
                           "Tell me who wins and at what price."),
}


def render():
    st.header("02. Multi-Router Comparison")
    st.caption("Branch: `examples-advanced` | ReAct vs PlanExecute vs CodeGen")

    preset = st.selectbox("Preset Questions", ["Custom"] + list(PRESETS.keys()))
    if preset != "Custom":
        question = st.text_area("Question", PRESETS[preset], height=100)
    else:
        question = st.text_area("Question", "Enter your question here...", height=100)

    if st.button("Run All Routers") and question and require_api_key():
        results = {}

        col1, col2, col3 = st.columns(3)
        router_configs = [
            (col1, "ReAct", "ReActRouter"),
            (col2, "PlanExecute", "PlanExecuteRouter"),
            (col3, "CodeGen", "CodeGenRouter"),
        ]

        for col, name, router_cls in router_configs:
            with col:
                st.subheader(name)
                with st.spinner(f"{name} processing..."):
                    start = time.time()
                    response = asyncio.run(_run_router(router_cls, question))
                    elapsed = time.time() - start

                results[name] = {"response": response, "time": elapsed}
                st.metric("Time", f"{elapsed:.1f}s")
                st.text_area(f"{name} Answer", response[:500], height=150, key=f"ans_{name}",
                            disabled=True)

        # Comparison chart
        st.markdown("---")
        st.subheader("Performance Comparison")

        fig = go.Figure()
        names = list(results.keys())
        times = [results[n]["time"] for n in names]
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1"]

        fig.add_trace(go.Bar(
            x=names, y=times,
            marker_color=colors,
            text=[f"{t:.1f}s" for t in times],
            textposition="auto",
        ))
        fig.update_layout(
            title="Response Time Comparison",
            yaxis_title="Time (seconds)",
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("""
**Router Characteristics:**
- **ReAct**: Think \u2192 Act \u2192 Observe loop. Good for iterative reasoning.
- **PlanExecute**: Plan first, then execute step by step. Good for complex multi-step tasks.
- **CodeGen**: Generate code to solve. Most token-efficient for computation tasks.
        """)


async def _run_router(router_cls_name, question):
    from agentsociety2_lite.env import ReActRouter, PlanExecuteRouter, CodeGenRouter
    from agentsociety2_lite.contrib import SimpleSocialSpace

    router_map = {
        "ReActRouter": ReActRouter,
        "PlanExecuteRouter": PlanExecuteRouter,
        "CodeGenRouter": CodeGenRouter,
    }

    env = SimpleSocialSpace(agent_id_name_pairs=[(1, "Tester")])
    router = router_map[router_cls_name](env_modules=[env])
    return await router.route(question, system="You are a helpful analytical assistant.")
