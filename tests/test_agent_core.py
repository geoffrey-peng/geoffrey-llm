"""Tests for the Agent loop: feedback, parallel tools, budgets, history."""

import asyncio
import json

import pytest

from geoffrey_llm.agent import Agent, tool
from geoffrey_llm.geocode.models.base import BaseModel, ModelConfig, ModelResponse


class FakeModel(BaseModel):
    """Scripted model: pops pre-programmed responses, records every call."""

    def __init__(self, script):
        super().__init__(ModelConfig(model_name="fake"))
        self.script = list(script)
        self.calls = []

    @property
    def provider_name(self):
        return "fake"

    async def chat(self, messages, tools=None, **kwargs):
        self.calls.append([dict(m) for m in messages])
        assert self.script, "模型被调用的次数超过脚本响应数"
        return self.script.pop(0)

    async def stream(self, messages, tools=None, **kwargs):
        raise AssertionError("agent 循环不应使用 stream()")
        yield  # pragma: no cover


def tool_call_response(name, arguments, call_id="call_1", content="", usage=None):
    return ModelResponse(
        content=content,
        finish_reason="tool_calls",
        usage=usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        tool_calls=[
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)},
            }
        ],
    )


def text_response(text, usage=None):
    return ModelResponse(
        content=text,
        finish_reason="stop",
        usage=usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    )


@tool
def add(a: int, b: int) -> int:
    """加法。"""
    return a + b


@tool
def boom() -> str:
    """总是失败。"""
    raise RuntimeError("炸了")


def make_agent(script, **kwargs):
    model = FakeModel(script)
    return Agent(model=model, tools=[add, boom], **kwargs), model


def test_loop_feeds_tool_result_back():
    agent, model = make_agent(
        [
            tool_call_response("add", {"a": 1, "b": 2}, call_id="call_1", content="我来算"),
            text_response("结果是 3"),
        ]
    )
    result = asyncio.run(agent.arun("1+2=?"))

    assert result.output == "结果是 3"
    assert result.finish_reason == "stop"
    assert result.iterations == 2

    # 第二次调用时,历史里必须是 assistant(tool_calls) + tool 结果,且 id 对得上
    second = model.calls[1]
    assert [m["role"] for m in second] == ["user", "assistant", "tool"]
    assert second[1]["tool_calls"][0]["id"] == "call_1"
    assert second[2]["tool_call_id"] == "call_1"
    assert second[2]["content"] == "3"


def test_instructions_prepend_system_not_history():
    agent, model = make_agent([text_response("好")], instructions="你是助手")
    asyncio.run(agent.arun("hi"))
    assert model.calls[0][0] == {"role": "system", "content": "你是助手"}
    # system prompt 只在请求时拼接,不进入持久化历史
    assert agent.history[0]["role"] == "user"


def test_max_iterations_stops_loop():
    script = [tool_call_response("add", {"a": 1, "b": 2}, call_id=f"call_{i}") for i in range(10)]
    agent, model = make_agent(script, max_iterations=3)
    result = asyncio.run(agent.arun("loop"))

    assert result.finish_reason == "max_iterations"
    assert result.output is None
    assert result.iterations == 3
    assert len(model.calls) == 3


def test_parallel_tool_calls_ordered():
    two_calls = ModelResponse(
        content="",
        finish_reason="tool_calls",
        tool_calls=[
            {"id": "call_a", "type": "function", "function": {"name": "add", "arguments": '{"a": 1, "b": 1}'}},
            {"id": "call_b", "type": "function", "function": {"name": "add", "arguments": '{"a": 2, "b": 2}'}},
        ],
    )
    agent, _ = make_agent([two_calls, text_response("ok")])
    result = asyncio.run(agent.arun("x"))

    tool_msgs = [m for m in result.messages if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == ["call_a", "call_b"]
    assert tool_msgs[0]["content"] == "2"
    assert tool_msgs[1]["content"] == "4"


def test_tool_error_fed_back_not_raised():
    agent, _ = make_agent(
        [
            tool_call_response("boom", {}),
            text_response("收到错误,换条路"),
        ]
    )
    result = asyncio.run(agent.arun("试试"))
    assert result.output == "收到错误,换条路"
    tool_msgs = [m for m in result.messages if m["role"] == "tool"]
    assert "RuntimeError" in tool_msgs[0]["content"]


def test_bad_json_and_unknown_tool_fed_back():
    bad_json = ModelResponse(
        content="",
        finish_reason="tool_calls",
        tool_calls=[{"id": "call_x", "type": "function", "function": {"name": "add", "arguments": "{bad json"}}],
    )
    agent, _ = make_agent(
        [
            bad_json,
            tool_call_response("no_such_tool", {}, call_id="call_y"),
            text_response("恢复"),
        ]
    )
    result = asyncio.run(agent.arun("x"))
    assert result.output == "恢复"

    tool_msgs = [m for m in result.messages if m["role"] == "tool"]
    assert "JSON" in tool_msgs[0]["content"]
    assert "not found" in tool_msgs[1]["content"]


def test_history_persists_across_runs():
    agent, model = make_agent([text_response("第一轮"), text_response("第二轮")])
    asyncio.run(agent.arun("问1"))
    asyncio.run(agent.arun("问2"))

    assert [m["role"] for m in model.calls[1]] == ["user", "assistant", "user"]
    assert agent.history[-1]["content"] == "第二轮"


def test_explicit_history_branches():
    agent, model = make_agent([text_response("好")])
    asyncio.run(
        agent.arun(
            "新问题",
            history=[
                {"role": "user", "content": "旧上下文"},
                {"role": "assistant", "content": "旧的回答"},
            ],
        )
    )
    assert [m["role"] for m in model.calls[0]] == ["user", "assistant", "user"]


def test_usage_accumulated_across_iterations():
    agent, _ = make_agent(
        [
            tool_call_response("add", {"a": 1, "b": 2}, usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}),
            text_response("3", usage={"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}),
        ]
    )
    result = asyncio.run(agent.arun("1+2"))
    assert result.usage == {"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45}


def test_astream_event_sequence():
    agent, _ = make_agent(
        [
            tool_call_response("add", {"a": 1, "b": 2}, call_id="call_1", content="我来算"),
            text_response("结果是 3"),
        ]
    )

    async def collect():
        return [event async for event in agent.astream("1+2=?")]

    events = asyncio.run(collect())
    types = [e.type for e in events]
    assert types == ["assistant", "tool_call", "tool_result", "final"]

    tool_call_event = events[1]
    assert tool_call_event.tool_name == "add"
    assert tool_call_event.arguments == {"a": 1, "b": 2}
    assert events[3].content == "结果是 3"


def test_sync_run_works_without_loop():
    agent, _ = make_agent([text_response("hi")])
    result = agent.run("hello")
    assert result.output == "hi"


def test_sync_run_rejected_inside_loop():
    async def in_loop():
        agent, _ = make_agent([text_response("hi")])
        with pytest.raises(RuntimeError):
            agent.run("hello")

    asyncio.run(in_loop())


def test_model_string_resolution():
    # provider 构造时强校验 key,测试传假 key;格式解析是重点
    agent = Agent(model="deepseek/deepseek-chat", api_key="test")
    assert agent.model.provider_name == "deepseek"
    assert agent.model.model == "deepseek-chat"


def test_invalid_model_and_tools_rejected():
    with pytest.raises(TypeError):
        Agent(model=123)
    with pytest.raises(TypeError):
        Agent(model="deepseek/x", api_key="test", tools=[lambda x: x])
