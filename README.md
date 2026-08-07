# geoffrey-llm

[![PyPI version](https://badge.fury.io/py/geoffrey-llm.svg)](https://pypi.org/project/geoffrey-llm/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

一个轻量的 LLM 工具包,包含机器学习、深度学习、agent 构建、博客客户端、大模型微调等独立子模块。每个模块依赖隔离,按需安装。

## 模块总览

| 模块 | 说明 | 安装 extras | 状态 |
|---|---|---|---|
| `geoffrey_llm.ml` | 机器学习(基于 sklearn,统一 API + 中文评估报表) | `[ml]` | ![Active](https://img.shields.io/badge/status-Active-green) |
| `geoffrey_llm.dl` | 深度学习(基于 torch,神经网络封装) | `[dl]` | ![Planned](https://img.shields.io/badge/status-Planned-lightgrey) |
| `geoffrey_llm.geocode` | 大模型 agent 构建(Claude Code 风格 REPL) | `[geocode]` | ![Alpha](https://img.shields.io/badge/status-Alpha-yellow) |
| `geoffrey_llm.blog` | 个人博客 REST API 客户端 | `[blog]` | ![Active](https://img.shields.io/badge/status-Active-green) |
| `geoffrey_llm.finetune` | 大模型微调(LoRA / QLoRA,基于 transformers/peft) | `[finetune]` | ![Planned](https://img.shields.io/badge/status-Planned-lightgrey) |

## 安装

```bash
# 只装机器学习
pip install geoffrey-llm[ml]

# 只装 agent REPL
pip install geoffrey-llm[geocode]

# 只装博客客户端
pip install geoffrey-llm[blog]

# 装全部(含 dev 工具)
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
├── geocode/        # agent 构建
│   ├── cli.py / repl.py
│   ├── models/ tools/ memory/ session/ cmd/ mcp/ prompts/
├── blog/           # 个人博客 REST API 客户端
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
- [ ] `geocode`: 更多 provider、工具系统增强
