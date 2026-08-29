"""
Geocode - A Claude Code-like coding assistant built on geoffrey-llm.

Simplified version of Claude Code with:
- Interactive REPL interface
- Memory system (file-based with YAML frontmatter)
- MCP server integration
- Multi-model support (kimi, deepseek, qwen, openai-compatible)
- Tool calling (file read/write/edit, bash)

公共 API 全部惰性导入:仅 ``from geoffrey_llm.geocode.models.base import ...``
这类子模块引用不应连带拉起 rich / prompt-toolkit 等重依赖。
"""

__version__ = "0.1.0"

_LAZY_EXPORTS = {
    "REPL": ("geoffrey_llm.geocode.cmd.repl", "REPL"),
    "run_repl": ("geoffrey_llm.geocode.cmd.repl", "run_repl"),
    "BaseModel": ("geoffrey_llm.geocode.models.base", "BaseModel"),
    "ModelResponse": ("geoffrey_llm.geocode.models.base", "ModelResponse"),
    "Tool": ("geoffrey_llm.geocode.tools.base", "Tool"),
    "ToolInput": ("geoffrey_llm.geocode.tools.base", "ToolInput"),
    "ToolResult": ("geoffrey_llm.geocode.tools.base", "ToolResult"),
    "MemoryStore": ("geoffrey_llm.geocode.memory.store", "MemoryStore"),
    "SessionManager": ("geoffrey_llm.geocode.session.manager", "SessionManager"),
}

__all__ = [
    "__version__",
    *_LAZY_EXPORTS,
]


def __getattr__(name: str):
    if name in _LAZY_EXPORTS:
        import importlib

        module_name, attr = _LAZY_EXPORTS[name]
        value = getattr(importlib.import_module(module_name), attr)
        globals()[name] = value  # 缓存,后续访问直接命中
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
