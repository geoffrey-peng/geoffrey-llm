"""
Base tool interface for geocode.

All tools (FileRead, FileWrite, Bash, etc.) implement this interface.
Inspired by Claude Code's tool system but simplified.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolInput(BaseModel):
    """Base input schema for tools."""
    pass


class ToolResult(BaseModel):
    """Result from tool execution."""

    success: bool = True
    output: Optional[str] = None
    error: Optional[str] = None

    # For tool call response format
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dict for API response."""
        result = {
            "success": self.success,
        }
        if self.output is not None:
            result["output"] = self.output
        if self.error is not None:
            result["error"] = self.error
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.tool_name:
            result["tool_name"] = self.tool_name
        return result


class Tool(ABC):
    """
    Abstract base class for all tools.

    Each tool provides:
    - name: Tool identifier for prompts
    - description: Human-readable description
    - input_schema: Pydantic model for validation
    - call(): Execute the tool
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name as used in prompts and tool call routing."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        pass

    @abstractmethod
    def input_schema(self) -> type[ToolInput]:
        """Return the Pydantic model class for input validation."""
        pass

    @abstractmethod
    async def call(self, input_data: ToolInput) -> ToolResult:
        """Execute the tool with validated input."""
        pass

    def validate_input(self, data: dict) -> ToolInput:
        """Validate input data against the schema."""
        schema = self.input_schema()
        return schema.model_validate(data)

    def get_schema(self) -> dict:
        """Get JSON schema for tool definition."""
        schema = self.input_schema()
        return schema.model_json_schema()


class ToolCall:
    """Represents a tool call from the model."""

    def __init__(
        self,
        name: str,
        arguments: dict,
        id: Optional[str] = None,
    ):
        self.name = name
        self.arguments = arguments
        self.id = id or f"call_{id(self)[:12]}"

    def __repr__(self) -> str:
        return f"ToolCall(name={self.name!r}, args={self.arguments!r})"


class ToolRegistry:
    """
    Registry for available tools.

    Usage:
        registry = ToolRegistry()
        registry.register(FileReadTool())
        registry.register(FileWriteTool())

        tool = registry.get("FileRead")
        result = await tool.call(input_data)
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """List all registered tools."""
        return list(self._tools.values())

    def get_tool_definitions(self) -> list[dict]:
        """Get tool definitions for API (OpenAI format)."""
        tools = []
        for tool in self._tools.values():
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.get_schema(),
                },
            })
        return tools


# Global registry
_default_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry()
        # Register built-in tools
        from geoffrey_llm.geocode.tools.file_read import FileReadTool
        from geoffrey_llm.geocode.tools.file_write import FileWriteTool
        from geoffrey_llm.geocode.tools.file_edit import FileEditTool
        from geoffrey_llm.geocode.tools.bash import BashTool

        _default_registry.register(FileReadTool())
        _default_registry.register(FileWriteTool())
        _default_registry.register(FileEditTool())
        _default_registry.register(BashTool())
    return _default_registry
