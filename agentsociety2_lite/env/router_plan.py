"""PlanExecute Router — plan first, then execute step by step."""

import json
import json_repair

from .router_base import RouterBase


class PlanExecuteRouter(RouterBase):
    """Router that creates a plan then executes each step."""

    async def route(
        self,
        question: str,
        system: str = "",
        readonly: bool = True,
    ) -> str:
        llm = self._get_llm()
        tools = self.get_all_tools(readonly_only=readonly)

        if not tools:
            return await llm.complete(question, system=system)

        tool_desc = "\n".join(
            f"- {t['name']}: {t['description']}"
            for t in tools
        )

        # Step 1: Plan
        plan_prompt = (
            f"Question: {question}\n\n"
            f"Available tools:\n{tool_desc}\n\n"
            f"Create a step-by-step plan to answer this question. "
            f"Return a JSON object with a 'steps' array of strings. "
            f"Each step should describe one action. Keep it concise (max 5 steps)."
        )
        plan_response = await llm.complete(plan_prompt, system=system)

        try:
            plan = json_repair.loads(plan_response)
            steps = plan.get("steps", [])
        except Exception:
            steps = [question]

        if not steps:
            steps = [question]

        # Step 2: Execute each step
        results = []
        for i, step in enumerate(steps[:5]):
            step_result = await llm.complete_with_tools(
                prompt=f"Execute this step: {step}\n\nContext from previous steps:\n" +
                       "\n".join(results[-3:]),
                tools=tools,
                system=system,
            )

            if step_result["tool_calls"]:
                for tc in step_result["tool_calls"]:
                    tr = self.call_tool(tc["name"], tc["args"])
                    results.append(f"Step {i+1} ({step}): {tr}")
            else:
                results.append(f"Step {i+1} ({step}): {step_result['text']}")

        # Step 3: Synthesize
        synthesis_prompt = (
            f"Original question: {question}\n\n"
            f"Execution results:\n" + "\n".join(results) + "\n\n"
            f"Provide a clear, comprehensive answer based on these results."
        )
        return await llm.complete(synthesis_prompt, system=system)
