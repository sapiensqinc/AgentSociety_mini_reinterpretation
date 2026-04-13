"""Environment base class with @tool decorator for LLM-callable methods."""

import inspect
from typing import Any, Callable, get_type_hints


def tool(readonly: bool = True, kind: str = "action"):
    """Decorator to mark a method as an LLM-callable tool."""
    def decorator(func: Callable) -> Callable:
        func._is_tool = True
        func._readonly = readonly
        func._kind = kind
        return func
    return decorator


def _python_type_to_json(annotation) -> str:
    if annotation is inspect.Parameter.empty or annotation is None:
        return "string"
    if annotation is int:
        return "integer"
    if annotation is float:
        return "number"
    if annotation is bool:
        return "boolean"
    if annotation is str:
        return "string"
    if annotation is list:
        return "array"
    if annotation is dict:
        return "object"
    origin = getattr(annotation, "__origin__", None)
    if origin is list:
        return "array"
    if origin is dict:
        return "object"
    return "string"


class EnvBase:
    """Base class for environment modules."""

    def __init__(self):
        self._tools_cache: list[dict[str, Any]] | None = None

    def get_tools(self, readonly_only: bool = False) -> list[dict[str, Any]]:
        """Get JSON schema for all @tool-decorated methods."""
        if self._tools_cache is not None and not readonly_only:
            return self._tools_cache

        tools = []
        for name in dir(self):
            if name.startswith("_"):
                continue
            method = getattr(self, name, None)
            if not callable(method) or not getattr(method, "_is_tool", False):
                continue
            if readonly_only and not method._readonly:
                continue

            sig = inspect.signature(method)
            hints = get_type_hints(method) if hasattr(method, "__annotations__") else {}
            properties: dict[str, Any] = {}
            required: list[str] = []

            for pname, param in sig.parameters.items():
                if pname == "self":
                    continue
                ptype = _python_type_to_json(hints.get(pname, param.annotation))
                prop: dict[str, Any] = {"type": ptype}
                if param.default is inspect.Parameter.empty:
                    required.append(pname)
                else:
                    prop["default"] = param.default
                properties[pname] = prop

            schema: dict[str, Any] = {
                "name": name,
                "description": (method.__doc__ or "").strip(),
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
                "_readonly": method._readonly,
                "_kind": method._kind,
            }
            tools.append(schema)

        if not readonly_only:
            self._tools_cache = tools
        return tools

    def call_tool(self, name: str, args: dict[str, Any]) -> str:
        """Call a tool method by name with given arguments."""
        method = getattr(self, name, None)
        if method is None or not getattr(method, "_is_tool", False):
            return f"Error: Unknown tool '{name}'"
        try:
            # Type-coerce arguments based on signature
            sig = inspect.signature(method)
            hints = get_type_hints(method) if hasattr(method, "__annotations__") else {}
            coerced = {}
            for pname, param in sig.parameters.items():
                if pname == "self":
                    continue
                if pname in args:
                    val = args[pname]
                    expected = hints.get(pname, param.annotation)
                    if expected is int and not isinstance(val, int):
                        val = int(val)
                    elif expected is float and not isinstance(val, float):
                        val = float(val)
                    elif expected is bool and not isinstance(val, bool):
                        val = bool(val)
                    coerced[pname] = val
                elif param.default is not inspect.Parameter.empty:
                    pass  # use default
                else:
                    return f"Error: Missing required argument '{pname}' for tool '{name}'"
            result = method(**coerced)
            return str(result)
        except Exception as e:
            return f"Error calling tool '{name}': {e}"
