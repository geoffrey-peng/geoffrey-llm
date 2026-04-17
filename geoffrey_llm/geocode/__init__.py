"""
Geocode - A Claude Code-like coding assistant built on geoffrey-llm.

Simplified version of Claude Code with:
- Interactive REPL interface
- Memory system (file-based with YAML frontmatter)
- MCP server integration
- Multi-model support (kimi, deepseek, qwen, openai-compatible)
- Tool calling (file read/write/edit, bash)
"""

__version__ = "0.1.0"

from geoffrey_llm.geocode.cmd.repl import REPL, run_repl
from geoffrey_llm.geocode.models.base import BaseModel, ModelResponse
from geoffrey_llm.geocode.tools.base import Tool, ToolInput, ToolResult
from geoffrey_llm.geocode.memory.store import MemoryStore
from geoffrey_llm.geocode.session.manager import SessionManager

__all__ = [
    "__version__",
    "REPL",
    "run_repl",
    "BaseModel",
    "ModelResponse",
    "Tool",
    "ToolInput",
    "ToolResult",
    "MemoryStore",
    "SessionManager",
]
