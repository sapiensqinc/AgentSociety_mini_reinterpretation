"""02. Multi-Router Comparison -- compare ReAct, PlanExecute, CodeGen."""

import asyncio
import time
import streamlit as st
import plotly.graph_objects as go
from app.config import require_api_key
from app.security import ready_to_run, sanitize_user_input, show_safe_error


DESCRIPTION = """
**논문 대응**: 논문 Section 5 "Large-scale Social Simulation Engine"의 시스템 아키텍처에 해당합니다.
논문(v1)에서는 에이전트가 환경 API를 직접 호출했지만, v2 코드에서는 에이전트와 환경 사이에
"라우터(Router)"라는 중간 계층을 도입하여 LLM이 자연어를 도구 호출로 자동 변환합니다.

**원본 코드 위치**: `agentsociety2/env/` 디렉토리에 5가지 라우터가 구현되어 있습니다.
`router_codegen.py`(CodeGen), `router_react.py`(ReAct), `router_plan_execute.py`(PlanExecute),
그리고 이들의 2단계 변형(TwoTier)이 있습니다. 이 예제에서는 핵심 3가지를 비교합니다.

**동작 원리**: 같은 질문이 각 라우터에 전달되면 서로 다른 전략으로 처리됩니다.
ReAct는 "생각-행동-관찰"을 반복하며 점진적으로 답에 접근합니다.
PlanExecute는 먼저 전체 계획을 세운 뒤 각 단계를 순차 실행합니다.
CodeGen은 Python 코드를 생성하여 실행하므로 계산 문제에 가장 효율적입니다.

**해결하는 문제**: 연구자가 실험 특성에 맞는 최적의 라우팅 전략을 선택할 수 있게 합니다.
단순 계산은 CodeGen이, 탐색적 질의는 ReAct가, 복잡한 다단계 태스크는 PlanExecute가 적합합니다.
토큰 사용량과 응답 시간의 트레이드오프를 직접 비교해볼 수 있습니다.
"""

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
    st.caption("Source: paper §5 · code `agentsociety2/env/router_*.py` · mini `agentsociety2_lite/env/router_*.py`")

    st.info(
        "**Purpose.** 같은 질문을 3가지 라우팅 전략으로 처리해 응답·토큰·시간 트레이드오프 비교.\n\n"
        "- **ReAct** — 생각·행동·관찰 반복 (탐색형 질의에 강함)\n"
        "- **PlanExecute** — 전체 계획 수립 후 단계 실행 (복잡한 다단계 태스크)\n"
        "- **CodeGen** — Python 코드 생성·실행 (계산/집계 태스크에 효율적)\n\n"
        "**Expected result.** 계산 문제는 CodeGen이 토큰 적고 빠름, 탐색은 ReAct가 유리, 다단계는 PlanExecute."
    )

    with st.expander("이 예제에 대하여 — 상세", expanded=False):
        st.markdown(DESCRIPTION)

    preset = st.selectbox("Preset Questions", ["Custom"] + list(PRESETS.keys()))
    if preset != "Custom":
        question = st.text_area("Question", PRESETS[preset], height=100)
    else:
        question = st.text_area("Question", "Enter your question here...", height=100)

    if st.button("Run All Routers") and question and ready_to_run(tag="multi_router"):
        try:
            question = sanitize_user_input(question)
        except ValueError as e:
            st.error(str(e))
            return

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
                    try:
                        response = asyncio.run(_run_router(router_cls, question))
                    except Exception as e:
                        show_safe_error(e, context=f"{name} failed")
                        return
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
- **ReAct**: Think -> Act -> Observe loop. Good for iterative reasoning.
- **PlanExecute**: Plan first, then execute step by step. Good for complex multi-step tasks.
- **CodeGen**: Generate code to solve. Most token-efficient for computation tasks.
        """)


async def _run_router(router_cls_name, question):
    from agentsociety2_lite import PersonAgent, AgentSociety
    from agentsociety2_lite.env import ReActRouter, PlanExecuteRouter, CodeGenRouter
    from agentsociety2_lite.contrib import SimpleSocialSpace
    from datetime import datetime

    router_map = {
        "ReActRouter": ReActRouter,
        "PlanExecuteRouter": PlanExecuteRouter,
        "CodeGenRouter": CodeGenRouter,
    }

    # Create agent for the society
    agent = PersonAgent(
        id=1,
        profile={
            "name": "Tester",
            "personality": "analytical and helpful",
        },
    )

    # Create router and register environment module
    env_router = router_map[router_cls_name]()
    env_router.register_module(
        SimpleSocialSpace(agent_id_name_pairs=[(agent.id, agent.name)])
    )

    # Create and run through AgentSociety
    society = AgentSociety(
        agents=[agent],
        env_router=env_router,
        start_t=datetime.now(),
    )
    await society.init()

    response = await society.ask(question)

    await society.close()
    return response
