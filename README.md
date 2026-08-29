# geoffrey-llm

[![PyPI version](https://badge.fury.io/py/geoffrey-llm.svg)](https://pypi.org/project/geoffrey-llm/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

一个轻量的 LLM 与多云工具包，包含机器学习、深度学习、agent 构建、大模型微调和多云资源管理模块。每个模块依赖隔离，按需安装。

## 模块总览

| 模块 | 说明 | 安装 extras | 状态 |
|---|---|---|---|
| `geoffrey_llm.ml` | 机器学习(基于 sklearn,统一 API + 中文评估报表) | `[ml]` | ![Active](https://img.shields.io/badge/status-Active-green) |
| `geoffrey_llm.dl` | 深度学习(基于 torch,神经网络封装) | `[dl]` | ![Planned](https://img.shields.io/badge/status-Planned-lightgrey) |
| `geoffrey_llm.geocode` | 大模型 agent 构建(Claude Code 风格 REPL) | `[geocode]` | ![Alpha](https://img.shields.io/badge/status-Alpha-yellow) |
| `geoffrey_llm.agent` | 最小 Agent 运行时(Agent + `@tool` + 事件流) | `[agent]` | ![Alpha](https://img.shields.io/badge/status-Alpha-yellow) |
| `geoffrey_llm.blog` | 个人博客 REST API 客户端 | `[blog]` | ![Active](https://img.shields.io/badge/status-Active-green) |
| `geoffrey_llm.audit` | 统一审计服务 SDK(装饰器/中间件 fire-and-forget 接入,纯标准库) | 无需 extra | ![Active](https://img.shields.io/badge/status-Active-green) |
| `geoffrey_llm.retrieval` | 检索 API 客户端(重排序 / BGE-M3 混合向量嵌入) | `[retrieval]` | ![Active](https://img.shields.io/badge/status-Active-green) |
| `geoffrey_llm.aistudio` | AIStudio 平台客户端(提示词 CRUD / 智能体调用) | `[aistudio]` | ![Active](https://img.shields.io/badge/status-Active-green) |
| `geoffrey_llm.finetune` | 大模型微调(LoRA / QLoRA,基于 transformers/peft) | `[finetune]` | ![Planned](https://img.shields.io/badge/status-Planned-lightgrey) |
| `geoffrey_llm.cloud` | 多云核心资源统一入口(阿里云/腾讯云/华为云/AWS) | `[cloud-*]` | ![Alpha](https://img.shields.io/badge/status-Alpha-yellow) |

## 安装

```bash
# 只装机器学习
pip install geoffrey-llm[ml]

# 只装 agent REPL
pip install geoffrey-llm[geocode]

# 只装博客客户端
pip install geoffrey-llm[blog]

# 只装检索客户端(重排序 / 嵌入)
pip install geoffrey-llm[retrieval]

# 只装 AIStudio 平台客户端(提示词管理 / 智能体调用)
pip install geoffrey-llm[aistudio]

# 只装 Agent 运行时
pip install geoffrey-llm[agent]

# 审计 SDK 纯标准库,基础包即可,无需 extra
pip install geoffrey-llm

# 只装 AWS 多云适配器（其余厂商对应 cloud-alibaba/cloud-tencent/cloud-huawei）
pip install geoffrey-llm[cloud-aws]

# 装全部(含 dev 工具；云 SDK 请按需装 cloud 或单厂商 cloud-*)
pip install geoffrey-llm[all]
```

## 快速上手

### 机器学习模块

```python
from geoffrey_llm.ml import Trainer, Evaluator

# 训练(分类)
trainer = Trainer(task="classification", model_name="random_forest")
trainer.fit(X_train, y_train)
preds = trainer.predict(X_test)

# 评估(中文报表)
print(Evaluator.classification_report(y_test, preds, chinese=True))

# 持久化
trainer.save("model.pkl")
trainer2 = Trainer.load("model.pkl", task="classification", model_name="random_forest")
```

支持的算法:
- **分类**: `random_forest` / `logistic_regression` / `svm` / `gradient_boosting`
- **回归**: `random_forest` / `linear_regression` / `gradient_boosting`

### agent 构建模块(geocode)

```bash
# 命令行启动 REPL
geocode
geocode --provider deepseek --model deepseek-chat
```

```python
from geoffrey_llm.geocode import REPL, BaseModel
from geoffrey_llm.geocode.models.base import get_registry, ModelConfig

config = ModelConfig(model_name="moonshot-v1-8k")
model = get_registry().create("kimi", config)
repl = REPL(model=model)
```

geocode 特性:
- 多模型: Kimi / DeepSeek / Qwen / OpenAI 兼容
- 工具调用: FileRead / FileWrite / FileEdit / Bash(带白名单)
- 文件式记忆系统(yaml frontmatter)
- 会话持久化与 resume
- MCP (Model Context Protocol) 集成

### Agent 运行时(agent)

`agent` 是 geocode 之上抽出的最小 Agent 框架层。设计哲学:**Agent = 受治理的循环**——循环本身几十行就能写完,框架的价值在循环之外:工具结果回灌、并行工具执行、迭代预算、事件流、可检视可持久化的对话历史。

```bash
export DEEPSEEK_API_KEY="your-key"  # 或其他 provider 的 key
```

```python
from geoffrey_llm.agent import Agent, tool

@tool
def search_posts(query: str, top_n: int = 5) -> str:
    """按关键词检索博客文章。

    Args:
        query: 搜索关键词
        top_n: 返回条数
    """
    ...  # 任意同步或异步函数,入参 schema 自动从签名生成

agent = Agent(
    model="deepseek/deepseek-chat",   # provider/model,也接受 geocode 的 BaseModel 实例
    tools=[search_posts],             # @tool 函数或 geocode 的 Tool 实例
    instructions="你是博客助手,回答前先检索资料。",
)

result = agent.run("总结最近关于 RAG 的文章")   # 同步;async 上下文用 await agent.arun(...)
print(result.output)       # 最终回答
print(result.iterations)   # 循环轮数
print(result.usage)        # 累计 token 用量
print(result.finish_reason)  # "stop" 或 "max_iterations"
```

事件流——边跑边看 agent 在干什么(适合做 UI / 审计):

```python
import asyncio

async def main():
    async for event in agent.astream("帮我查一下并写篇草稿"):
        if event.type == "assistant":
            print(f"[模型] {event.content}")
        elif event.type == "tool_call":
            print(f"[调用] {event.tool_name}({event.arguments})")
        elif event.type == "tool_result":
            print(f"[结果] {event.result.output}")
        elif event.type == "final":
            print(f"[完成] {event.content}")

asyncio.run(main())
```

要点:
- **回灌循环**:工具结果自动回传模型继续推理,直到模型不再请求工具;`max_iterations`(默认 25)兜底
- **并行工具**:同一轮多个 tool call 并发执行,结果按顺序回填
- **错误自愈**:工具抛异常 / 参数 JSON 非法 / 工具不存在,都以错误文本回灌模型自行纠正,不打断循环
- **历史治理**:`agent.history` 不含 system prompt,可跨轮累积、可传入 `history=` 分叉重放;REPL 与会话持久化共用同一循环
- `agent.default_tools()` 提供内置的 FileRead / FileWrite / FileEdit / Bash 四件套

### 博客客户端

博客客户端调用博客的 `API_TOKEN`，不是 Flask 的 `SECRET_KEY`。支持的环境变量优先级为 `BLOG_API_TOKEN`、`BLOG_SECRET`、`BLOG_SERCET`；`BLOG_SERCET` 用于兼容已有配置。

```bash
export BLOG_BASE_URL="https://blog.geoffrey-peng.cc"
export BLOG_SERCET="your-blog-api-token"
```

```python
from geoffrey_llm.blog import BlogClient

with BlogClient() as blog:
    posts = blog.list_posts(page=1, per_page=10)
    blog.create_post(
        title="SDK 发布",
        slug="sdk-release",
        content="通过 geoffrey-llm 发布。",
        category_id=1,
        is_public=True,
    )
```

支持分类、文章 CRUD 和分享链接管理：`list_categories`、`list_posts`、`get_post`、`create_post`、`update_post`、`delete_post`、`create_share`、`list_shares`、`revoke_share`。

### 检索客户端(retrieval)

`retrieval` 对接 `https://api.geoffrey-peng.cc/api/v1`，提供 RAG 流程中的召回精排两件套：`rerank`（候选文档相关性精排）与 `embeddings`（BGE-M3 稠密 + 稀疏混合向量）。

```bash
export RETRIEVAL_API_KEY="your-api-key"
```

```python
from geoffrey_llm.retrieval import RetrievalClient

with RetrievalClient() as client:
    # 精排：按与 query 的相关性给候选文档排序
    rerank_result = client.rerank(
        query="什么是深度学习？",
        documents=["深度学习是AI的一个子领域。", "今天午饭吃什么？"],
        top_n=1,
    )
    print(rerank_result["results"])

    # 嵌入：单个字符串或列表均可，返回 dense_vec + sparse_vec
    embed = client.embeddings("BGE-M3模型支持多语言混合检索")
    assert len(embed["data"][0]["dense_vec"]) == 1024
```

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `RETRIEVAL_API_KEY` | — | 检索 API Key(必填) |
| `RETRIEVAL_BASE_URL` | `https://api.geoffrey-peng.cc/api/v1` | 接口根地址 |

### AIStudio 平台客户端(aistudio)

对接自建 LLM 网关平台(Geo Lab / api-platform),提供两类能力:

**1. 提示词管理**(需要平台管理员令牌)

```python
from geoffrey_llm.aistudio import AIStudioClient

with AIStudioClient(base_url="http://localhost:8001", admin_token="eyJ...") as cli:
    # 列出全部(含停用);list_prompts() 为公开只读,仅返回已启用
    for p in cli.list_prompts(include_inactive=True):
        print(p["id"], p["name"])       # id 为 UUID,创建后固定

    p = cli.create_prompt(name="翻译助手", content="你是一个专业翻译...",
                          category="翻译", description="中英互译")
    cli.get_prompt(p["id"])             # 按 ID 查看
    cli.update_prompt(p["id"], description="新描述", is_active=False)
    cli.delete_prompt(p["id"])          # 删除
```

> 提示词 ID 是平台生成的 UUID(如 `3e4b2bf6-9498-...`),不是从 1 开始的数字序号,
> 创建后即可用于查看 / 修改 / 删除与 SDK 调用。

**2. 智能体调用**(使用发布后创建的 `agent-xxx` Key,管理员令牌亦可调试)

```python
with AIStudioClient(base_url="http://localhost:8001",
                    admin_token="eyJ...", agent_api_key="agent-xxx") as cli:
    for a in cli.list_agents()["agents"]:
        print(a["app_id"], a["name"], a["status"])   # 仅 published 可被 API 调用

    reply = cli.chat(
        app_id="app-7eb4e3e92d7a4e11a86d",
        messages=[{"role": "user", "content": "帮我总结一下这份文档"}],
    )
    print(reply["content"])             # 回答
    print(reply["sources"])             # 引用的知识库切片
```

环境变量:`AISTUDIO_BASE_URL` / `AISTUDIO_ADMIN_TOKEN` / `AISTUDIO_AGENT_KEY`。

### 审计接入(audit)

`audit` 把应用接入统一审计服务 [audit.geoffrey-peng.cc](https://audit.geoffrey-peng.cc)。纯标准库实现、零额外依赖;后台线程批量投递,发送失败只告警,**绝不阻塞或影响业务**。未配置时所有调用静默 no-op,应用可以无条件内置审计代码。

```bash
# 密钥在审计 UI 的「应用」页(/apps)创建
export AUDIT_ENDPOINT="https://audit.geoffrey-peng.cc/api/v1/events"
export AUDIT_APP="myapp"
export AUDIT_KEY="xxxx"
```

**方式一:装饰器**——业务动作审计,自动记录耗时与成败,异常原样抛出不吞:

```python
from geoffrey_llm.audit import audit_event

@audit_event(action="post.delete", actor_from="username",
             resource_type="post", resource_id_from="post_id")
def delete_post(username, post_id):
    ...  # 同步 / async 函数均可
```

**方式二:中间件**——Web 请求自动审计,各一行:

```python
# FastAPI / Starlette(ASGI)
from geoffrey_llm.audit import AuditASGIMiddleware
app = AuditASGIMiddleware(app)

# Flask(WSGI)
from geoffrey_llm.audit import AuditWSGIMiddleware
app.wsgi_app = AuditWSGIMiddleware(app.wsgi_app)
```

**方式三:手动发送**:

```python
from geoffrey_llm.audit import audit
audit("share.create", "share.create", resource_id=str(share_id), actor_name="geoffrey")
```

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `AUDIT_ENDPOINT` | — | 审计服务 ingest 地址(必填) |
| `AUDIT_APP` | — | 应用名,与 UI 创建的一致(必填) |
| `AUDIT_KEY` | — | 应用密钥(必填) |
| `AUDIT_ENABLED` | 三项齐备即启用 | 强制开关(`1/true/yes` 或 `0/false/no`) |
| `AUDIT_BATCH_SIZE` | 20 | 批量大小(服务端上限 100) |
| `AUDIT_FLUSH_INTERVAL` | 1.0 秒 | 攒批最长等待 |
| `AUDIT_QUEUE_SIZE` | 1000 | 内存队列上限,满则丢弃 |
| `AUDIT_TIMEOUT_SECONDS` | 2.0 | 发送超时 |

metadata 中的敏感键(password/token/secret/cookie 等)客户端与服务端双重脱敏。博客现用的独立 `audit_client.py` 后续可平滑迁移到本模块。

### 多云客户端

`cloud` 提供实例、VPC/子网、安全组、对象存储和托管数据库的统一入口。`provider` 与 `region` 可直接用 `Provider` / `Region` 常量点选，无需手写字符串。默认只读；安全组规则变更还必须显式打开变更权限并关闭 dry-run。凭据仅由各官方 SDK 的环境变量、配置文件或工作负载角色链解析，不能写入代码或 `CloudConfig`。

```python
from geoffrey_llm.cloud import CloudClient, CloudConfig, Provider, Region

cloud = CloudClient(CloudConfig(provider=Provider.AWS, region=Region.AWS.AP_SOUTHEAST_1))
instances = cloud.instances.list()
security_groups = cloud.security_groups.list()
buckets = cloud.object_storage.list_buckets()
```

本地无凭据验证可使用内存 Mock provider：

```python
cloud = CloudClient(CloudConfig(provider=Provider.MOCK, region=Region.ALIBABA.CN_BEIJING))
assert cloud.databases.list()[0].id == "db-demo"
```

官方资料与资源映射存放在仓库根目录 [`.cloud/`](.cloud/)，其中不允许保存密钥或真实资源标识。

## 设计原则

- **依赖隔离**:`import geoffrey_llm` 不拉任何重依赖,各模块按 extras 安装
- **中文友好**:错误信息、评估报表默认中文
- **统一 API**:不同后端(sklearn / lightgbm / xgboost)共用 `Trainer` 入口
- **混合实现**:核心算法用主流库,周边工具(评估/报表/记忆/会话)自己写

## 项目结构

```
geoffrey_llm/
├── common/         # 共享:Registry / BaseConfig / GeoffreyError
├── ml/             # 机器学习
│   ├── trainer.py
│   ├── evaluator.py
│   ├── report.py
│   ├── models.py
│   └── backends/
├── dl/             # 深度学习(占位)
├── agent/          # 最小 Agent 运行时
│   ├── core.py     #   Agent 循环 / 事件流 / 结果
│   ├── tool.py     #   @tool 装饰器(函数 → 工具)
│   └── builtins.py #   geocode 内置工具快捷入口
├── geocode/        # agent 构建(REPL 基于 agent 循环)
│   ├── cli.py / repl.py
│   ├── models/ tools/ memory/ session/ cmd/ mcp/ prompts/
├── blog/           # 个人博客 REST API 客户端
├── cloud/          # 多云统一入口(client/config/constants/models/providers)
├── retrieval/      # 检索 API 客户端(重排序 / 嵌入)
└── finetune/       # 大模型微调(占位)
```

## License

MIT

## Roadmap

- [ ] `ml`: lightgbm / xgboost 后端
- [ ] `ml`: 场景化 pipeline(表格分类一键流程)
- [ ] `ml`: 特征工程 / 自动调参 / 模型解释性
- [ ] `dl`: CNN / RNN / Transformer 封装,DLTrainer
- [ ] `finetune`: LoRATrainer / QLoRATrainer / DatasetPreprocessor
- [x] `agent`: 最小 Agent 运行时(循环回灌 / `@tool` / 事件流),geocode REPL 迁移至该循环
- [ ] `agent`: token 级流式输出(含流式 tool call 聚合)
- [ ] `agent`: 审计(audit)与权限门禁原生集成
- [ ] `geocode`: 更多 provider、工具系统增强
