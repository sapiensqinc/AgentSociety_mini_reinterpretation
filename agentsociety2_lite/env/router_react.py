"""ReAct Router — Reason + Act iteratively."""

from .router_base import RouterBase


class ReActRouter(RouterBase):
    """Router using ReAct (Reasoning and Acting) pattern."""

    def __init__(self, env_modules=None, max_iterations: int = 5):
        super().__init__(env_modules)
        self.max_iterations = max_iterations

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
            f"- {t['name']}: {t['description']} (params: {list(t['parameters']['properties'].keys())})"
            for t in tools
        )

        react_system = (
            f"{system}\n\n"
            f"You have access to these tools:\n{tool_desc}\n\n"
            f"Use the ReAct pattern:\n"
            f"Thought: reason about what to do\n"
            f"Action: tool_name(arg1=val1, arg2=val2)\n"
            f"Observation: (tool result will be provided)\n"
            f"... repeat as needed ...\n"
            f"Final Answer: your final response\n\n"
            f"If no tool is needed, go directly to Final Answer."
        )

        history = f"Question: {question}\n"

        for i in range(self.max_iterations):
            response = await llm.complete(history, system=react_system)
            history += response + "\n"

            if "Final Answer:" in response:
                return response.split("Final Answer:")[-1].strip()

            # Try function calling
            result = await llm.complete_with_tools(
                prompt=history,
                tools=tools,
                system=react_system,
            )

            if result["tool_calls"]:
                for tc in result["tool_calls"]:
                    tr = self.call_tool(tc["name"], tc["args"])
                    history += f"Observation: {tr}\n"
            elif "Action:" in response:
                # Parse action from text
                import re
                match = re.search(r"Action:\s*(\w+)\(([^)]*)\)", response)
                if match:
                    name = match.group(1)
                    args_str = match.group(2)
                    args = {}
                    for pair in args_str.split(","):
                        pair = pair.strip()
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            v = v.strip().strip("'\"")
                            args[k.strip()] = v
                    tr = self.call_tool(name, args)
                    history += f"Observation: {tr}\n"
                else:
                    break
            else:
                break

        # Final synthesis
        return await llm.complete(
            f"{history}\n\nBased on all the above, provide your Final Answer:",
            system=react_system,
        )
