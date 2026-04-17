# geoffrey-llm

[![PyPI version](https://badge.fury.io/py/geoffrey-llm.svg)](https://pypi.org/project/geoffrey-llm/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A lightweight toolkit for LLM fine-tuning, inference optimization, and agent development.

## Features

- **geocode** - Claude Code-like coding assistant with interactive REPL
  - Multi-model support (Kimi, DeepSeek, Qwen, OpenAI-compatible)
  - Memory system with file-based storage
  - MCP (Model Context Protocol) integration
  - Tool calling (File read/write/edit, Bash)
- More features coming soon (LoRA fine-tuning, GraphRAG, etc.)

## Installation

```bash
pip install geoffrey-llm
```

### Install with all features

```bash
pip install geoffrey-llm[all]
```

### Install geocode only

```bash
pip install geoffrey-llm[geocode]
```

## Quick Start

### Using geocode (REPL)

```bash
# After installing geocode
geocode

# Or specify provider
geocode --provider deepseek --model deepseek-chat
```

### Python API

```python
from geoffrey_llm.geocode import REPL

# Create REPL with default settings
repl = REPL()

# Or with specific provider
from geoffrey_llm.geocode.models.base import get_registry, ModelConfig

config = ModelConfig(model_name="moonshot-v1-8k")
registry = get_registry()
model = registry.create("kimi", config)
repl = REPL(model=model)
```

## geocode Module

geocode is a Claude Code-like coding assistant with:

### Features

- **Interactive REPL** - Terminal-based chat interface
- **Multi-Model Support** - Works with Kimi, DeepSeek, Qwen, and any OpenAI-compatible API
- **Memory System** - Persistent memory with file-based storage
- **MCP Integration** - Connect to MCP servers for extended capabilities
- **Tool Calling** - Built-in tools for file operations and shell commands

### Supported Models

| Provider | Model Names | Environment Variable |
|----------|-------------|---------------------|
| Kimi (Moonshot) | moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k | `KIMI_API_KEY` |
| DeepSeek | deepseek-chat, deepseek-coder | `DEEPSEEK_API_KEY` |
| Qwen (DashScope) | qwen-turbo, qwen-plus, qwen-max | `DASHSCOPE_API_KEY` |
| OpenAI-compatible | gpt-3.5-turbo, gpt-4, llama3, etc. | `OPENAI_API_KEY` |

### Configuration

Create `~/.geoffrey/config.yaml`:

```yaml
model:
  provider: kimi
  model_name: moonshot-v1-8k
  api_key: ${KIMI_API_KEY}  # Or set env var directly
```

### Commands in REPL

| Command | Description |
|---------|-------------|
| `exit`, `quit` | End session |
| `/new` | Start new session |
| `/resume <id>` | Resume existing session |
| `/sessions` | List all sessions |
| `/memory save <type> <content>` | Save a memory |
| `/memory list [type]` | List memories |
| `/memory recall <query>` | Search memories |
| `/mcp list` | List MCP servers |

### Memory Types

| Type | Description |
|------|-------------|
| `user` | User preferences, identity |
| `feedback` | User corrections, feedback |
| `project` | Project-specific context |
| `reference` | External reference material |

### MCP Servers

Configure MCP servers in `~/.geoffrey/mcp.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "env": {}
    }
  }
}
```

### Tool Calling

geocode supports tool calling with built-in tools:

- **FileRead** - Read files with line offset/limit
- **FileWrite** - Write content to files
- **FileEdit** - Edit files using search/replace
- **Bash** - Execute shell commands (sandboxed)

## Memory System

Memories are stored as markdown files with YAML frontmatter in `~/.geoffrey/memory/`:

```markdown
---
id: mem_abc123
type: user
created_at: 2026-04-18T10:00:00Z
updated_at: 2026-04-18T10:00:00Z
tags:
  - preference
---
User prefers dark mode interface.
```

## Session Management

Sessions are stored as JSON files in `~/.geoffrey/sessions/`. Each session contains:

- Conversation history
- Project context
- Model/ provider settings
- Last active timestamp

## License

MIT License

## Roadmap

- [ ] LoRA/QLoRA fine-tuning interface
- [ ] Unified inference backend (vLLM, llama.cpp, TensorRT)
- [ ] GraphRAG-lite for knowledge graph RAG
- [ ] Log analysis Agent toolkit
- [ ] Model quantization utilities (AWQ, GPTQ)
