"""Function-to-tool adapter for geoffrey_llm.agent.

The ``@tool`` decorator turns a plain Python function (sync or async) into a
:class:`Tool` the agent loop can call. The input schema is generated from the
function signature; the description and per-parameter descriptions come from
the docstring (Google style, ``Args:`` / ``参数:`` sections both accepted).

Usage:
    @tool
    def search(query: str, top_n: int = 5) -> str:
        \"\"\"按关键词检索文章。

        Args:
            query: 搜索关键词
            top_n: 返回条数
        \"\"\"
        ...
"""

import asyncio
import inspect
import json
import re
from typing import Any, Callable, Optional

from pydantic import Field, create_model

from geoffrey_llm.geocode.tools.base import Tool, ToolInput, ToolResult

# ``name: desc`` / ``name (type): desc`` / 中文冒号均可
_PARAM_LINE = re.compile(r"^(\w+)\s*(?:\([^)]*\))?\s*[:：]\s*(.*)$")
_ARG_SECTIONS = ("args:", "arguments:", "parameters:", "参数:")
_END_SECTIONS = ("returns:", "raises:", "yields:", "example", "note", "返回", "示例")


def _parse_docstring(doc: str) -> tuple[str, dict[str, str]]:
    """Split a docstring into (description, {param_name: description})."""
    description_lines: list[str] = []
    params: dict[str, str] = {}
    in_args = False
    current: Optional[str] = None

    for line in doc.splitlines():
        stripped = line.strip()

        if not in_args:
            if stripped.lower() in _ARG_SECTIONS or stripped.rstrip(":").lower() in _ARG_SECTIONS:
                in_args = True
            else:
                description_lines.append(line)
            continue

        # Inside the args section.
        if not stripped:
            continue
        if stripped.lower().startswith(_END_SECTIONS):
            break
        match = _PARAM_LINE.match(stripped)
        if match:
            current = match.group(1)
            params[current] = match.group(2).strip()
        elif current is not None:
            # Indented continuation of the previous parameter description.
            params[current] += " " + stripped.lstrip("-* ")
        else:
            break

    return "\n".join(description_lines).strip(), params


def _result_to_text(result: Any) -> str:
    """Coerce a tool return value into model-friendly text."""
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, ensure_ascii=False, default=str)
    except TypeError:
        return str(result)


class FunctionTool(Tool):
    """A :class:`Tool` backed by an arbitrary Python function."""

    def __init__(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self._func = func
        self._name = name or func.__name__
        doc = inspect.getdoc(func) or ""
        doc_description, param_docs = _parse_docstring(doc)
        self._description = description if description is not None else doc_description
        self._param_docs = param_docs
        self._schema_model = self._build_schema()

    def _build_schema(self) -> type[ToolInput]:
        fields: dict[str, tuple] = {}
        signature = inspect.signature(self._func)
        for param_name, param in signature.parameters.items():
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            annotation = (
                param.annotation if param.annotation is not inspect.Parameter.empty else Any
            )
            default = (
                param.default if param.default is not inspect.Parameter.empty else ...
            )
            fields[param_name] = (
                annotation,
                Field(default=default, description=self._param_docs.get(param_name)),
            )
        return create_model(f"{self._name}_input", **fields)

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description or "No description provided."

    def input_schema(self) -> type[ToolInput]:
        return self._schema_model

    async def call(self, input_data: ToolInput) -> ToolResult:
        kwargs = input_data.model_dump()
        if inspect.iscoroutinefunction(self._func):
            result = await self._func(**kwargs)
        else:
            # 同步函数放线程池,避免阻塞事件循环。
            result = await asyncio.to_thread(self._func, **kwargs)
        return ToolResult(success=True, output=_result_to_text(result))


def tool(func: Optional[Callable] = None, *, name: Optional[str] = None, description: Optional[str] = None):
    """Decorator that turns a function into an agent-callable tool.

    Can be used bare (``@tool``) or with overrides (``@tool(name=..., description=...)``).
    Both sync and async functions are supported; sync functions run in a worker
    thread so they never block the event loop.
    """

    def wrapper(fn: Callable) -> FunctionTool:
        return FunctionTool(fn, name=name, description=description)

    if func is not None:
        return wrapper(func)
    return wrapper
