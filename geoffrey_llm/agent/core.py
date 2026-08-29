"""Minimal agent runtime: a governed loop over model + tools.

Philosophy: the agent loop itself is ~50 lines — nobody needs a framework to
write one. What a framework owes you is everything around the loop: feeding
tool results back to the model, parallel tool execution, iteration budgets,
event streams for UIs, and a conversation history you can inspect and persist.

Usage:
    agent = Agent(
        model="deepseek/deepseek-chat",
        tools=[search, write_post],
        instructions="你是博客助手,回答前先检索资料。",
    )

    result = await agent.arun("总结最近关于 RAG 的文章")
    print(result.output, result.iterations, result.usage)

    # Or consume events as they happen (for UIs):
    async for event in agent.astream("..."):
        ...
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import AsyncIterator, Iterable, Optional, Union

from geoffrey_llm.geocode.models.base import (
    BaseModel,
    ModelConfig,
    get_registry,
)
from geoffrey_llm.geocode.tools.base import Tool, ToolRegistry, ToolResult

DEFAULT_MAX_ITERATIONS = 25


@dataclass
class AgentResult:
    """Final outcome of one ``run``."""

    output: Optional[str] = None
    messages: list[dict] = field(default_factory=list)
    iterations: int = 0
    finish_reason: str = "stop"  # "stop" | "max_iterations"
    usage: dict = field(default_factory=dict)


@dataclass
class AgentEvent:
    """Streaming event emitted while the loop runs.

    Types:
        assistant      — interim model text (usually alongside tool calls)
        tool_call      — the model asked to call a tool (not yet executed)
        tool_result    — tool finished, ``result`` holds the ToolResult
        final          — last model text, loop is done
        max_iterations — iteration budget exhausted without a final answer
    """

    type: str
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    arguments: Optional[dict] = None
    result: Optional[ToolResult] = None
    iterations: int = 0
    usage: dict = field(default_factory=dict)


def _resolve_model(
    model: Union[str, BaseModel],
    *,
    temperature: Optional[float],
    max_tokens: Optional[int],
    api_key: Optional[str],
    base_url: Optional[str],
    timeout: Optional[int],
) -> BaseModel:
    """Accept either a provider string (``"deepseek/deepseek-chat"``) or a ready model."""
    if isinstance(model, BaseModel):
        return model
    if isinstance(model, str):
        provider, _, model_name = model.partition("/")
        overrides = {}
        if temperature is not None:
            overrides["temperature"] = temperature
        if max_tokens is not None:
            overrides["max_tokens"] = max_tokens
        if api_key is not None:
            overrides["api_key"] = api_key
        if base_url is not None:
            overrides["base_url"] = base_url
        if timeout is not None:
            overrides["timeout"] = timeout
        # 不带 "/" 时 model_name 为空串,交给各 provider 自己的 DEFAULT_MODEL 兜底。
        config = ModelConfig(model_name=model_name, **overrides)
        return get_registry().create(provider, config)
    raise TypeError(
        f"model 必须是 'provider/model' 字符串或 BaseModel 实例,收到: {type(model).__name__}"
    )


def _build_registry(tools) -> ToolRegistry:
    """Accept a ToolRegistry, an iterable of tools, or None (no tools)."""
    if tools is None:
        return ToolRegistry()
    if isinstance(tools, ToolRegistry):
        return tools
    if isinstance(tools, Iterable):
        registry = ToolRegistry()
        for item in tools:
            if isinstance(item, Tool):
                registry.register(item)
            else:
                raise TypeError(
                    f"工具 {item!r} 不是 Tool 实例。普通函数请先用 @tool 装饰, "
                    f"或使用 geoffrey_llm.agent.default_tools() 获取内置工具。"
                )
        return registry
    raise TypeError(f"tools 必须是 Tool 列表或 ToolRegistry,收到: {type(tools).__name__}")


def _accumulate_usage(total: dict, usage: Optional[dict]) -> None:
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        total[key] = total.get(key, 0) + (usage or {}).get(key, 0)


class Agent:
    """A model + tools + a loop that keeps calling the model until it is done.

    The agent keeps its conversation history in ``self.history`` (without the
    system prompt; the system prompt is prepended per call). Pass an explicit
    ``history=`` to branch a run off an existing transcript — useful for the
    REPL and for resuming sessions.
    """

    def __init__(
        self,
        model: Union[str, BaseModel],
        tools=None,
        instructions: Optional[str] = None,
        *,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.model = _resolve_model(
            model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
        self.tools = _build_registry(tools)
        self.instructions = instructions
        self.max_iterations = max_iterations
        self.history: list[dict] = []

    def reset(self) -> None:
        """Clear conversation history."""
        self.history = []

    async def astream(
        self,
        user_input: str,
        *,
        history: Optional[list[dict]] = None,
        instructions: Optional[str] = None,
    ) -> AsyncIterator[AgentEvent]:
        """Run the loop, yielding :class:`AgentEvent` as things happen."""
        base = list(history) if history is not None else list(self.history)
        system_prompt = instructions if instructions is not None else self.instructions

        messages = list(base)
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
        messages.append({"role": "user", "content": user_input})
        offset = 1 if system_prompt else 0

        tool_defs = self.tools.get_tool_definitions() or None
        usage_total: dict = {}
        iterations = 0
        finish_reason = "stop"
        final_content: Optional[str] = None

        while True:
            iterations += 1
            if iterations > self.max_iterations:
                finish_reason = "max_iterations"
                yield AgentEvent(
                    type="max_iterations",
                    iterations=iterations - 1,
                    usage=usage_total,
                )
                break

            response = await self.model.chat(messages, tools=tool_defs)
            _accumulate_usage(usage_total, response.usage)

            if response.tool_calls:
                # 助手消息必须原样带回 tool_calls,后续 tool 消息才能对上 id。
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": response.tool_calls,
                    }
                )
                if response.content:
                    yield AgentEvent(
                        type="assistant", content=response.content, iterations=iterations
                    )
                for tool_call in response.tool_calls:
                    arguments = _parse_arguments(tool_call)
                    yield AgentEvent(
                        type="tool_call",
                        tool_name=(tool_call.get("function") or {}).get("name"),
                        tool_call_id=tool_call.get("id"),
                        arguments=arguments if isinstance(arguments, dict) else None,
                        iterations=iterations,
                    )
                pairs = await asyncio.gather(
                    *(self._execute_tool(tc) for tc in response.tool_calls)
                )
                for tool_call, result in pairs:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": result.tool_call_id,
                            "content": result.output or result.error or "",
                        }
                    )
                    yield AgentEvent(
                        type="tool_result",
                        tool_name=result.tool_name,
                        tool_call_id=result.tool_call_id,
                        result=result,
                        iterations=iterations,
                    )
                continue

            final_content = response.content or ""
            messages.append({"role": "assistant", "content": final_content})
            yield AgentEvent(
                type="final",
                content=final_content,
                iterations=iterations,
                usage=usage_total,
            )
            break

        self.history = messages[offset:]

    async def arun(
        self,
        user_input: str,
        *,
        history: Optional[list[dict]] = None,
        instructions: Optional[str] = None,
    ) -> AgentResult:
        """Run the loop to completion and return an :class:`AgentResult`."""
        finish_reason = "stop"
        output: Optional[str] = None
        usage: dict = {}
        iterations = 0
        async for event in self.astream(
            user_input, history=history, instructions=instructions
        ):
            if event.type == "final":
                finish_reason, output, usage, iterations = (
                    "stop",
                    event.content,
                    event.usage,
                    event.iterations,
                )
            elif event.type == "max_iterations":
                finish_reason, output, usage, iterations = (
                    "max_iterations",
                    None,
                    event.usage,
                    event.iterations,
                )
        return AgentResult(
            output=output,
            messages=self.history,
            iterations=iterations,
            finish_reason=finish_reason,
            usage=usage,
        )

    def run(self, user_input: str, **kwargs) -> AgentResult:
        """Sync convenience wrapper around :meth:`arun`."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(user_input, **kwargs))
        raise RuntimeError(
            "当前线程已有运行中的事件循环,请在 async 上下文使用 await agent.arun(...)"
        )

    async def _execute_tool(self, tool_call: dict) -> tuple[dict, ToolResult]:
        function = tool_call.get("function") or {}
        name = function.get("name")
        call_id = tool_call.get("id")
        arguments = _parse_arguments(tool_call)
        if isinstance(arguments, str):
            error_result = ToolResult(
                success=False,
                error=f"工具 {name} 的参数不是合法 JSON: {arguments!r}",
                tool_call_id=call_id,
                tool_name=name,
            )
            return tool_call, error_result

        registered = self.tools.get(name)
        if registered is None:
            return tool_call, ToolResult(
                success=False,
                error=f"Tool '{name}' not found",
                tool_call_id=call_id,
                tool_name=name,
            )

        try:
            validated = registered.validate_input(arguments)
            result = await registered.call(validated)
        except Exception as exc:  # noqa: BLE001 — 工具失败要回灌给模型,不能打断循环
            result = ToolResult(
                success=False,
                error=f"{type(exc).__name__}: {exc}",
                tool_call_id=call_id,
                tool_name=name,
            )
        result.tool_call_id = call_id
        result.tool_name = name
        return tool_call, result


def _parse_arguments(tool_call: dict) -> Union[dict, str]:
    """Parse a tool call's arguments; never raises — a bad string comes back as-is."""
    raw = (tool_call.get("function") or {}).get("arguments")
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw
    return parsed if isinstance(parsed, dict) else raw
