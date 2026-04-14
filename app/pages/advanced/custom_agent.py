"""01. Custom Agent -- specialist and recursive CoT agents."""

import asyncio
import streamlit as st
from app.config import require_api_key
from app.security import ready_to_run, cap, sanitize_user_input, show_safe_error


def render():
    st.header("01. Custom Agent")
    st.caption("Branch: `examples-advanced`")

    with st.expander("이 예제에 대하여", expanded=False):
        st.markdown("""
**논문 대응**: 논문 Section 3 전체, 특히 Section 3.2 "Emotion, Needs, and Cognition"과
Section 3.6 "Workflow"에 해당합니다. 논문에서 에이전트는 감정-욕구-인지의 고정 파이프라인을 가졌지만,
v2 코드에서는 AgentBase를 상속하여 자유롭게 행동 로직을 커스터마이징할 수 있도록 설계가 바뀌었습니다.

**원본 코드 위치**: `agentsociety2/agent/base.py`의 `AgentBase` 클래스를 상속하는 패턴입니다.
원본에서는 `PersonAgent` 외에도 스킬 기반 확장, 메모리 시스템 연동 등 다양한 커스텀 에이전트를 지원합니다.

**동작 원리**: SpecialistAgent는 `ask()` 메서드를 오버라이드하여 질문에 전문 분야 컨텍스트를 자동 주입합니다.
RecursiveAgent는 Chain-of-Thought(CoT) 패턴으로 질문을 하위 질문으로 분해한 뒤 각각 답변하고 종합합니다.
이는 논문에서 말하는 "인지(Cognition)" 계층의 서로 다른 구현 방식을 보여줍니다.

**해결하는 문제**: 동일한 AgentBase 인터페이스 위에서 다양한 추론 전략을 실험할 수 있음을 보여줍니다.
단순 질의응답(Specialist)부터 다단계 분석(CoT)까지, `ask()` 하나만 오버라이드하면 에이전트의 사고 방식 자체를 바꿀 수 있습니다.
        """)

    tab1, tab2, tab3 = st.tabs(["Specialist Agent", "Reflection", "Recursive CoT"])

    with tab1:
        st.subheader("Specialist Agent")
        specialty = st.text_input("Specialty", "climate science and environmental policy")
        question = st.text_input("Question", "What should cities do to prepare for extreme weather?",
                                  key="spec_q")

        if st.button("Ask Specialist", key="run_spec") and ready_to_run(tag="custom_agent"):
            try:
                specialty = sanitize_user_input(specialty)
                question = sanitize_user_input(question)
            except ValueError as e:
                st.error(str(e))
                return
            with st.spinner("Specialist is thinking..."):
                try:
                    response, enhanced = asyncio.run(_run_specialist(specialty, question))
                except Exception as e:
                    show_safe_error(e, context="Failed to process request")
                    return
            with st.expander("Internal Enhancement (actual prompt sent)"):
                st.code(enhanced)
            st.success(response)

    with tab2:
        st.subheader("Specialty Reflection")
        refl_specialty = st.text_input("Specialty", "environmental science", key="refl_spec")
        if st.button("Reflect", key="run_refl") and ready_to_run(tag="custom_agent"):
            try:
                refl_specialty = sanitize_user_input(refl_specialty)
            except ValueError as e:
                st.error(str(e))
                return
            with st.spinner("Reflecting..."):
                try:
                    response = asyncio.run(_run_reflection(refl_specialty))
                except Exception as e:
                    show_safe_error(e, context="Failed to process request")
                    return
            st.success(response)

    with tab3:
        st.subheader("Recursive Agent (Chain-of-Thought)")
        cot_question = st.text_input("Question", "How can we reduce urban traffic congestion?",
                                      key="cot_q")
        depth = cap("cot_depth", st.slider("Recursion Depth", 1, 3, 2))

        if st.button("Think Deeply", key="run_cot") and ready_to_run(tag="custom_agent"):
            try:
                cot_question = sanitize_user_input(cot_question)
            except ValueError as e:
                st.error(str(e))
                return
            with st.spinner("Decomposing and analyzing..."):
                try:
                    result = asyncio.run(_run_cot(cot_question, depth))
                except Exception as e:
                    show_safe_error(e, context="Failed to process request")
                    return

            if result["sub_questions"]:
                st.markdown("**Step 1: Decompose**")
                for i, sq in enumerate(result["sub_questions"]):
                    with st.expander(f"Sub-Q{i+1}: {sq['question'][:60]}..."):
                        st.write(sq["answer"])

                st.markdown("**Step 2: Synthesize**")
                st.success(result["synthesis"])
            else:
                st.success(result["synthesis"])


async def _run_specialist(specialty, question):
    from agentsociety2_lite import CodeGenRouter, AgentSociety
    from agentsociety2_lite.contrib import SimpleSocialSpace
    from agentsociety2_lite.agent.base import AgentBase
    from datetime import datetime

    class SpecialistAgent(AgentBase):
        def __init__(self, id, profile, specialty, **kw):
            super().__init__(id=id, profile=profile, **kw)
            self._specialty = specialty

        def _enhance_prompt(self, question):
            return (f"You are a specialist in {self._specialty}. "
                    f"Answer from this perspective: {question}")

        async def ask(self, question, readonly=True):
            enhanced = self._enhance_prompt(question)
            return await super().ask(enhanced, readonly=readonly)

        async def reflect_on_specialty(self):
            question = (
                f"As a specialist in {self._specialty}, "
                "what do you consider to be the most important aspects of your field?"
            )
            return await super().ask(question, readonly=True)

    agent = SpecialistAgent(id=1, profile={"name": "Dr. Climate", "personality": "scientific"},
                            specialty=specialty)
    env = SimpleSocialSpace(agent_id_name_pairs=[(1, "Dr. Climate")])
    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=[agent], env_router=router, start_t=datetime.now())
    await society.init()

    # Build the enhanced prompt for display, but call ask() which returns a string
    enhanced = agent._enhance_prompt(question)
    response = await agent.ask(question)
    await society.close()
    return response, enhanced


async def _run_reflection(specialty):
    from agentsociety2_lite import CodeGenRouter, AgentSociety
    from agentsociety2_lite.contrib import SimpleSocialSpace
    from agentsociety2_lite.agent.base import AgentBase
    from datetime import datetime

    class SpecialistAgent(AgentBase):
        def __init__(self, id, profile, specialty, **kw):
            super().__init__(id=id, profile=profile, **kw)
            self._specialty = specialty

        async def ask(self, question, readonly=True):
            enhanced = (f"You are a specialist in {self._specialty}. "
                        f"Answer from this perspective: {question}")
            return await super().ask(enhanced, readonly=readonly)

        async def reflect_on_specialty(self):
            question = (
                f"As a specialist in {self._specialty}, "
                "what do you consider to be the most important aspects of your field?"
            )
            return await super().ask(question, readonly=True)

    agent = SpecialistAgent(id=1, profile={"name": "Dr. Science", "personality": "curious"},
                            specialty=specialty)
    env = SimpleSocialSpace(agent_id_name_pairs=[(1, "Dr. Science")])
    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=[agent], env_router=router, start_t=datetime.now())
    await society.init()
    response = await agent.reflect_on_specialty()
    await society.close()
    return response


async def _run_cot(question, depth):
    from agentsociety2_lite import CodeGenRouter, AgentSociety
    from agentsociety2_lite.contrib import SimpleSocialSpace
    from agentsociety2_lite.agent.base import AgentBase
    import json_repair
    from datetime import datetime

    class RecursiveAgent(AgentBase):
        """An agent that uses chain-of-thought reasoning by recursively
        decomposing questions into sub-questions."""

        async def ask(self, question, readonly=True, depth=2):
            if depth <= 0:
                return await super().ask(question, readonly=readonly)

            # Step 1: ask the agent to break down the question
            breakdown_prompt = (
                f"Break down this question into sub-questions: {question}\n"
                "Respond with a JSON object containing a 'sub_questions' array of strings. Max 3."
            )
            breakdown = await super().ask(breakdown_prompt, readonly=True)

            # Parse sub-questions
            try:
                parsed = json_repair.loads(breakdown)
                sub_questions = parsed.get("sub_questions", [])[:3]
            except Exception:
                sub_questions = []

            if not sub_questions:
                return await super().ask(question, readonly=readonly)

            # Step 2: answer each sub-question recursively at reduced depth
            sub_answers = []
            for sq in sub_questions:
                answer = await self.ask(sq, readonly=True, depth=depth - 1)
                sub_answers.append(f"Q: {sq}\nA: {answer}")

            # Step 3: synthesize final answer
            synthesis_prompt = (
                f"Original question: {question}\n\n"
                f"Sub-question analysis:\n" + "\n".join(sub_answers) + "\n\n"
                "Based on the above analysis, provide a comprehensive answer "
                "to the original question."
            )
            return await super().ask(synthesis_prompt, readonly=readonly)

    agent = RecursiveAgent(id=1, profile={"name": "Deep Thinker", "personality": "analytical"})
    env = SimpleSocialSpace(agent_id_name_pairs=[(1, "Deep Thinker")])
    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=[agent], env_router=router, start_t=datetime.now())
    await society.init()

    # First, do the decomposition at depth=1 to capture sub-questions for display
    breakdown_prompt = (
        f"Break down this question into sub-questions: {question}\n"
        "Respond with a JSON object containing a 'sub_questions' array of strings. Max 3."
    )
    breakdown = await agent.ask(breakdown_prompt, readonly=True, depth=0)

    sub_questions = []
    try:
        parsed = json_repair.loads(breakdown)
        sqs = parsed.get("sub_questions", [])[:3]
    except Exception:
        sqs = []

    for sq in sqs:
        answer = await agent.ask(sq, readonly=True, depth=max(0, depth - 1))
        sub_questions.append({"question": sq, "answer": answer})

    if sub_questions:
        context = "\n".join(f"Q: {s['question']}\nA: {s['answer']}" for s in sub_questions)
        synthesis = await agent.ask(
            f"Original: {question}\n\nSub-analysis:\n{context}\n\n"
            "Provide a comprehensive answer to the original question.",
            readonly=True,
            depth=0,
        )
    else:
        synthesis = await agent.ask(question, readonly=True, depth=depth)

    await society.close()
    return {"sub_questions": sub_questions, "synthesis": synthesis}
