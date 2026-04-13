"""01. Custom Agent — specialist and recursive CoT agents."""

import asyncio
import streamlit as st
from app.config import require_api_key


def render():
    st.header("01. Custom Agent")
    st.caption("Branch: `examples-advanced` | AgentBase \uc0c1\uc18d \ucee4\uc2a4\ud130\ub9c8\uc774\uc9d5")

    tab1, tab2, tab3 = st.tabs(["Specialist Agent", "Reflection", "Recursive CoT"])

    with tab1:
        st.subheader("Specialist Agent")
        specialty = st.text_input("Specialty", "climate science and environmental policy")
        question = st.text_input("Question", "What should cities do to prepare for extreme weather?",
                                  key="spec_q")

        if st.button("Ask Specialist", key="run_spec") and require_api_key():
            with st.spinner("Specialist is thinking..."):
                response, enhanced = asyncio.run(_run_specialist(specialty, question))
            with st.expander("Internal Enhancement (actual prompt sent)"):
                st.code(enhanced)
            st.success(response)

    with tab2:
        st.subheader("Specialty Reflection")
        refl_specialty = st.text_input("Specialty", "environmental science", key="refl_spec")
        if st.button("Reflect", key="run_refl") and require_api_key():
            with st.spinner("Reflecting..."):
                response = asyncio.run(_run_reflection(refl_specialty))
            st.success(response)

    with tab3:
        st.subheader("Recursive Agent (Chain-of-Thought)")
        cot_question = st.text_input("Question", "How can we reduce urban traffic congestion?",
                                      key="cot_q")
        depth = st.slider("Recursion Depth", 1, 3, 2)

        if st.button("Think Deeply", key="run_cot") and require_api_key():
            with st.spinner("Decomposing and analyzing..."):
                result = asyncio.run(_run_cot(cot_question, depth))

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
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
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
            return await super().ask(enhanced, readonly=readonly), enhanced

    agent = SpecialistAgent(id=1, profile={"name": "Dr. Climate", "personality": "scientific"},
                            specialty=specialty)
    env = SimpleSocialSpace(agent_id_name_pairs=[(1, "Dr. Climate")])
    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=[agent], env_router=router, start_t=datetime.now())
    await society.init()
    response, enhanced = await agent.ask(question)
    await society.close()
    return response, enhanced


async def _run_reflection(specialty):
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from agentsociety2_lite.contrib import SimpleSocialSpace
    from datetime import datetime

    agent = PersonAgent(id=1, profile={"name": "Dr. Science", "personality": "curious"})
    env = SimpleSocialSpace(agent_id_name_pairs=[(1, "Dr. Science")])
    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=[agent], env_router=router, start_t=datetime.now())
    await society.init()
    q = f"As a specialist in {specialty}, what do you consider the most important aspects of your field?"
    response = await society.ask(q)
    await society.close()
    return response


async def _run_cot(question, depth):
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from agentsociety2_lite.contrib import SimpleSocialSpace
    from agentsociety2_lite.llm.client import get_client
    import json_repair
    from datetime import datetime

    agent = PersonAgent(id=1, profile={"name": "Deep Thinker", "personality": "analytical"})
    env = SimpleSocialSpace(agent_id_name_pairs=[(1, "Deep Thinker")])
    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=[agent], env_router=router, start_t=datetime.now())
    await society.init()

    # Decompose
    llm = get_client()
    breakdown = await llm.complete(
        f"Break down this question into sub-questions: {question}\n"
        f"Return a JSON with a 'sub_questions' array of strings. Max 3.",
        system="You are an analytical thinker."
    )

    sub_questions = []
    try:
        parsed = json_repair.loads(breakdown)
        sqs = parsed.get("sub_questions", [])[:3]
    except Exception:
        sqs = []

    for sq in sqs:
        answer = await society.ask(sq)
        sub_questions.append({"question": sq, "answer": answer})

    if sub_questions:
        context = "\n".join(f"Q: {s['question']}\nA: {s['answer']}" for s in sub_questions)
        synthesis = await llm.complete(
            f"Original: {question}\n\nSub-analysis:\n{context}\n\nProvide comprehensive answer.",
            system="Synthesize the analysis."
        )
    else:
        synthesis = await society.ask(question)

    await society.close()
    return {"sub_questions": sub_questions, "synthesis": synthesis}
