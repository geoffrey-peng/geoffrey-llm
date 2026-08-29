"""geoffrey_llm.agent — 最小 Agent 运行时。

设计哲学:Agent = 受治理的循环。循环本身几十行就能写完,
框架的价值在循环之外——工具结果回灌、并行执行、迭代预算、
事件流、可检视可持久化的对话历史。

    from geoffrey_llm.agent import Agent, tool

    @tool
    def search(query: str) -> str:
        \"\"\"按关键词检索。\"\"\"
        ...

    agent = Agent(model="deepseek/deepseek-chat", tools=[search])
    result = agent.run("帮我查一下")
"""

from geoffrey_llm.agent.core import Agent, AgentEvent, AgentResult, DEFAULT_MAX_ITERATIONS
from geoffrey_llm.agent.tool import FunctionTool, tool
from geoffrey_llm.agent.builtins import default_tools

__version__ = "0.1.0"

__all__ = [
    "Agent",
    "AgentEvent",
    "AgentResult",
    "DEFAULT_MAX_ITERATIONS",
    "FunctionTool",
    "tool",
    "default_tools",
    "__version__",
]
