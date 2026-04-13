"""CodeGen Router — generates Python code to call tools, then executes it."""

from typing import Any

from .router_base import RouterBase


class CodeGenRouter(RouterBase):
    """Router that generates Python code to interact with environment tools."""

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

        # Try function calling first
        result = await llm.complete_with_tools(
            prompt=question,
            tools=tools,
            system=system,
        )

        # Process tool calls if any
        if result["tool_calls"]:
            tool_results = []
            for tc in result["tool_calls"]:
                tr = self.call_tool(tc["name"], tc["args"])
                tool_results.append(f"Tool {tc['name']}({tc['args']}): {tr}")

            # Feed tool results back to LLM for final answer
            followup = (
                f"Original question: {question}\n\n"
                f"Tool results:\n" + "\n".join(tool_results) + "\n\n"
                f"Based on these tool results, provide a clear answer to the original question."
            )
            return await llm.complete(followup, system=system)

        return result["text"] or await llm.complete(question, system=system)
