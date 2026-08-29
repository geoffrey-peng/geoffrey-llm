"""geoffrey_llm.agent demo — 迷你博客助手(离线工具 + 真实模型)。

工具全部操作内存数据,不发任何网络请求;只有模型调用需要 key:

    export DEEPSEEK_API_KEY=sk-xxx          # 或改用下面的 DEMO_MODEL
    python examples/agent_demo.py

想换模型:export DEMO_MODEL="kimi/moonshot-v1-8k" (deepseek/kimi/qwen/openai)
"""

import asyncio
import os

from geoffrey_llm.agent import Agent, tool

DEMO_MODEL = os.environ.get("DEMO_MODEL", "deepseek/deepseek-chat")

# ---------- 内存数据(演示用,可替换为 geoffrey_llm.retrieval / blog 客户端) ----------

DOCS = [
    {"title": "RAG 入门", "text": "RAG 通过先检索后生成,让模型引用外部知识,适合知识频繁更新、需要溯源的场景。"},
    {"title": "微调简介", "text": "LoRA/QLoRA 微调改变模型本身的行为与风格,适合任务固定、有高质量标注数据的场景。"},
    {"title": "混合检索", "text": "混合检索结合稠密向量与稀疏关键词召回,再用重排序模型精排,是 RAG 召回层的常用方案。"},
]
POSTS: dict[str, str] = {}


@tool
def search_docs(query: str) -> str:
    """在知识库里检索与问题相关的资料片段。

    Args:
        query: 搜索关键词,空格分隔多个词
    """
    words = query.split()
    hits = [d for d in DOCS if any(w in d["text"] or w in d["title"] for w in words)]
    hits = hits or DOCS  # 检索不到就全部给出,保证演示能继续
    return "\n".join(f"-《{h['title']}》:{h['text']}" for h in hits[:3])


@tool
def create_post(title: str, content: str) -> str:
    """把文章草稿发布到博客(演示环境写入内存)。

    Args:
        title: 文章标题
        content: 正文,markdown 格式
    """
    POSTS[title] = content
    return f"已发布《{title}》,博客现共 {len(POSTS)} 篇文章。"


@tool
def list_posts() -> str:
    """列出博客现有的文章标题。"""
    return "\n".join(f"- {t}" for t in POSTS) or "(博客还没有文章)"


INSTRUCTIONS = (
    "你是博客助手。回答问题前先用 search_docs 检索资料,基于资料作答;"
    "用户让你写文章时,先检索、再成文,并用 create_post 发布。回答用中文。"
)


# ---------- 演示 1:事件流(Q&A) ----------


async def stream_demo():
    print("=" * 60)
    print(f"演示 1:事件流  model={DEMO_MODEL}")
    print("=" * 60)
    agent = Agent(model=DEMO_MODEL, tools=[search_docs], instructions=INSTRUCTIONS)

    async for event in agent.astream("RAG 和微调各适合什么场景?"):
        if event.type == "assistant":
            print(f"\n[模型] {event.content}")
        elif event.type == "tool_call":
            print(f"\n[调用] {event.tool_name}({event.arguments})")
        elif event.type == "tool_result":
            print(f"[工具] {event.result.output[:80]}...")
        elif event.type == "final":
            print(f"\n[回答]\n{event.content}")


# ---------- 演示 2:一步到位(agent.run) ----------


def run_demo():
    print("\n" + "=" * 60)
    print(f"演示 2:run() 写作并发布  model={DEMO_MODEL}")
    print("=" * 60)
    agent = Agent(
        model=DEMO_MODEL,
        tools=[search_docs, create_post, list_posts],
        instructions=INSTRUCTIONS,
    )

    result = agent.run("基于资料写一篇 200 字短文《RAG 还是微调?》并发到博客")
    print(result.output)
    print(
        f"\n--- {result.iterations} 轮循环 | "
        f"{result.usage.get('total_tokens', 0)} tokens | "
        f"finish={result.finish_reason} ---"
    )
    print("博客现状:")
    print(agent.run("列一下博客现有文章").output)


if __name__ == "__main__":
    asyncio.run(stream_demo())
    run_demo()
