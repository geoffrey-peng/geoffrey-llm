"""Tests that the REPL delegates chat handling to the agent loop."""

import asyncio

from geoffrey_llm.agent import tool
from geoffrey_llm.geocode.cmd.repl import REPL
from geoffrey_llm.geocode.models.base import BaseModel, ModelConfig, ModelResponse
from geoffrey_llm.geocode.tools.base import ToolRegistry


class FakeModel(BaseModel):
    def __init__(self, script):
        super().__init__(ModelConfig(model_name="fake"))
        self.script = list(script)
        self.calls = []

    @property
    def provider_name(self):
        return "fake"

    async def chat(self, messages, tools=None, **kwargs):
        self.calls.append([dict(m) for m in messages])
        return self.script.pop(0)

    async def stream(self, messages, tools=None, **kwargs):
        raise AssertionError("REPL 循环不应使用 stream()")
        yield  # pragma: no cover


class StubOutput:
    """Captures REPL rendering without pulling the terminal in."""

    def __init__(self):
        self.lines = []

    def print(self, *args, **kwargs):
        self.lines.append(("raw", " ".join(str(a) for a in args)))

    def print_banner(self):
        pass

    def print_help(self):
        pass

    def print_markdown(self, text):
        self.lines.append(("md", text))

    def print_dim(self, text):
        self.lines.append(("dim", text))

    def print_error(self, text):
        self.lines.append(("error", text))

    def print_info(self, text):
        self.lines.append(("info", text))

    def print_success(self, text):
        self.lines.append(("success", text))


@tool
def add(a: int, b: int) -> int:
    """加法。"""
    return a + b


def make_repl(script):
    model = FakeModel(script)
    registry = ToolRegistry()
    registry.register(add)
    repl = REPL(model=model, tools=registry)
    repl.output = StubOutput()
    return repl, model


def feed_input(repl, *lines):
    inputs = iter(lines)

    async def fake_input():
        return next(inputs)

    repl._get_input = fake_input


def test_repl_runs_tool_loop_until_final_answer():
    script = [
        ModelResponse(
            content="我来算一下",
            finish_reason="tool_calls",
            tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "add", "arguments": '{"a": 1, "b": 2}'}}],
        ),
        ModelResponse(content="结果是 3", finish_reason="stop"),
    ]
    repl, model = make_repl(script)
    feed_input(repl, "算一下 1+2", "exit")

    asyncio.run(repl.run())

    # 模型被调用两次:第一次拿到 tool_calls,第二次看到工具结果后给出最终回答
    assert len(model.calls) == 2
    tool_msgs = [m for m in model.calls[1] if m["role"] == "tool"]
    assert tool_msgs and tool_msgs[0]["content"] == "3"

    # 最终回答渲染到界面
    kinds = [text for kind, text in repl.output.lines if kind == "md"]
    assert "结果是 3" in kinds

    # 会话历史完整:user → assistant(tool_calls) → tool → assistant(final)
    assert [m["role"] for m in repl.messages] == ["user", "assistant", "tool", "assistant"]


def test_repl_error_keeps_history_for_retry():
    class BrokenModel(FakeModel):
        async def chat(self, messages, tools=None, **kwargs):
            raise ConnectionError("网络挂了")

    repl, _ = make_repl([])
    repl.model = BrokenModel([])
    # REPL.__init__ 已用旧 model 建好 agent,同步替换
    repl.agent.model = repl.model

    feed_input(repl, "随便说点", "exit")
    asyncio.run(repl.run())

    # 失败后 user 消息仍在历史里,可以原样重试
    assert repl.messages[0] == {"role": "user", "content": "随便说点"}
    assert any(kind == "error" for kind, _ in repl.output.lines)
