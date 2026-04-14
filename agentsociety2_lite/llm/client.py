"""Gemini LLM client — replaces litellm with direct google-genai SDK.

Security:
- In local development, API key is loaded from .env.local (gitignored).
- In deployed (Streamlit Cloud) environment, .env files are not present;
  the key must be supplied by the caller via set_api_key() in session state.
- Gemini safety filters are set to BLOCK_MEDIUM_AND_ABOVE for all categories.
- Output token cap prevents runaway generation.
"""

import os
import asyncio
from typing import Any

from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load .env.local (dev secrets) then .env (defaults). Both gitignored.
# In Streamlit Cloud deployment these files don't exist — key must come from session_state.
try:
    load_dotenv(".env.local", override=True)
    load_dotenv(".env", override=False)
except Exception:
    pass  # dotenv absence is acceptable in deployed environments

# Output limit to prevent runaway generation / cost overflow
MAX_OUTPUT_TOKENS = 2048

# Global singleton (but reinstantiated when API key changes)
_client: "GeminiClient | None" = None
_cached_key: str = ""


def get_client() -> "GeminiClient":
    """Return the Gemini client, rebuilding it if the API key has changed."""
    global _client, _cached_key
    current_key = os.getenv("GEMINI_API_KEY", "")
    if _client is None or current_key != _cached_key:
        _client = GeminiClient(api_key=current_key or None)
        _cached_key = current_key
    return _client


def _safety_settings() -> list[types.SafetySetting]:
    """Strictest practical safety: block medium and above for all categories."""
    categories = [
        "HARM_CATEGORY_HARASSMENT",
        "HARM_CATEGORY_HATE_SPEECH",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "HARM_CATEGORY_DANGEROUS_CONTENT",
    ]
    return [
        types.SafetySetting(category=c, threshold="BLOCK_MEDIUM_AND_ABOVE")
        for c in categories
    ]


class GeminiClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        if not self.api_key:
            raise RuntimeError(
                "Gemini API key not provided. Users must enter their own key via the sidebar."
            )
        self._client = genai.Client(api_key=self.api_key)

    async def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
    ) -> str:
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            safety_settings=_safety_settings(),
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
            max_output_tokens=MAX_OUTPUT_TOKENS,
            safety_settings=_safety_settings(),
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
