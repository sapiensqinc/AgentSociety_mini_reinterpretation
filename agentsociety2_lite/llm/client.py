"""Gemini LLM client — replaces litellm with direct google-genai SDK."""

import os
import asyncio
import inspect
from typing import Any

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Global singleton
_client: "GeminiClient | None" = None


def get_client() -> "GeminiClient":
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client


class GeminiClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self._client = genai.Client(api_key=self.api_key)

    async def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
    ) -> str:
        config = types.GenerateContentConfig(
            temperature=temperature,
        )
        if system:
            config.system_instruction = system

        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=self.model,
            contents=prompt,
            config=config,
        )
        return response.text or ""

    async def complete_with_tools(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        system: str = "",
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Call LLM with function-calling tools.

        Returns dict with:
          - "text": str (text response if any)
          - "tool_calls": list of {"name": str, "args": dict}
        """
        gemini_tools = self._convert_tools(tools)

        config = types.GenerateContentConfig(
            temperature=temperature,
            tools=gemini_tools,
        )
        if system:
            config.system_instruction = system

        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=self.model,
            contents=prompt,
            config=config,
        )

        result: dict[str, Any] = {"text": "", "tool_calls": []}

        for candidate in response.candidates or []:
            for part in candidate.content.parts or []:
                if part.text:
                    result["text"] += part.text
                if part.function_call:
                    result["tool_calls"].append({
                        "name": part.function_call.name,
                        "args": dict(part.function_call.args) if part.function_call.args else {},
                    })

        return result

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[types.Tool]:
        """Convert our tool schema format to Gemini Tool format."""
        declarations = []
        for t in tools:
            params = t.get("parameters", {})
            properties = params.get("properties", {})
            required = params.get("required", [])

            schema_props = {}
            for pname, pinfo in properties.items():
                ptype = pinfo.get("type", "string")
                gemini_type = {
                    "string": "STRING",
                    "integer": "INTEGER",
                    "number": "NUMBER",
                    "boolean": "BOOLEAN",
                    "array": "ARRAY",
                    "object": "OBJECT",
                }.get(ptype, "STRING")
                prop = {"type": gemini_type}
                if "description" in pinfo:
                    prop["description"] = pinfo["description"]
                schema_props[pname] = prop

            decl = types.FunctionDeclaration(
                name=t["name"],
                description=t.get("description", ""),
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        k: types.Schema(**v) for k, v in schema_props.items()
                    },
                    required=required,
                ) if schema_props else None,
            )
            declarations.append(decl)

        return [types.Tool(function_declarations=declarations)]
