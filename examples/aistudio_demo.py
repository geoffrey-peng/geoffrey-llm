"""AIStudio 客户端演示:提示词管理 + 智能体调用。

运行前准备:
    export AISTUDIO_BASE_URL=http://localhost:8001
    export AISTUDIO_ADMIN_TOKEN=<管理员登录返回的 access_token>
    export AISTUDIO_AGENT_KEY=<智能体发布后创建的 agent-xxx Key>  # 可选

    python examples/aistudio_demo.py
"""

from geoffrey_llm.aistudio import AIStudioClient


def main() -> None:
    with AIStudioClient() as cli:
        # ========== 1. 提示词管理 ==========
        print("== 提示词列表 ==")
        for p in cli.list_prompts():
            print(f"  [{p['id'][:8]}] {p['name']} ({p.get('category')})")

        created = cli.create_prompt(
            name="SDK 测试提示词",
            content="你是一个由 SDK 创建的测试助手,回答保持简短。",
            category="测试",
            description="aistudio_demo.py 创建",
        )
        print(f"已创建提示词, ID={created['id']}")  # UUID,非数字序号

        cli.update_prompt(created["id"], description="描述已被 SDK 修改")
        detail = cli.get_prompt(created["id"])
        print(f"修改后描述: {detail['description']}")

        # 在对话中使用该提示词
        reply = cli.chat(
            _first_app_id(cli),
            [{"role": "user", "content": "你好,请介绍你自己"}],
        )
        print("Agent 回复:", reply["content"][:100])
        if reply.get("sources"):
            print("引用知识库:", [s["kb"] for s in reply["sources"]])

        cli.delete_prompt(created["id"])
        print("已删除测试提示词")


def _first_app_id(cli: AIStudioClient) -> str:
    agents = cli.list_agents()["agents"]
    if not agents:
        raise SystemExit("平台中还没有智能体,请先在平台创建并发布")
    return agents[0]["app_id"]


if __name__ == "__main__":
    main()
