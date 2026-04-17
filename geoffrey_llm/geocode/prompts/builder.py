"""System prompt builder for geocode.

Inspired by Claude Code's array-based prompt composition with dynamic boundaries.
"""

from typing import TypedDict
from typing import Optional


SYSTEM_PROMPT_DYNAMIC_BOUNDARY = "__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__"


class PromptSection(TypedDict):
    """A single prompt section."""
    role: str
    content: str


class SystemPromptBuilder:
    """
    Array-based system prompt composition.

    Build prompts as arrays of sections that can be:
    - Static (cached globally)
    - Dynamic (session-specific)
    - Separated by __SYSTEM_PROMPT_DYNAMIC_BOUNDARY__
    """

    def __init__(self):
        self._static: list[PromptSection] = []
        self._dynamic: list[PromptSection] = []

    def add_static(self, content: str) -> "SystemPromptBuilder":
        """Add a static section (instructions, tools) - cached globally."""
        self._static.append({"role": "system", "content": content})
        return self

    def add_dynamic(self, content: str) -> "SystemPromptBuilder":
        """Add a dynamic section (memory, context) - session-specific."""
        self._dynamic.append({"role": "system", "content": content})
        return self

    def build(self) -> list[dict]:
        """
        Build final prompt array.

        Format:
        [
            {"role": "system", "content": "<static sections>"},
            {"role": "system", "content": "__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__\n\n<dynamic sections>"},
        ]
        """
        # Combine static sections
        static_content = "\n\n".join(s["content"] for s in self._static)

        # Build result
        result = [{"role": "system", "content": static_content}]

        # Add dynamic boundary if we have dynamic content
        if self._dynamic:
            dynamic_content = "\n\n".join(s["content"] for s in self._dynamic)
            result.append({
                "role": "system",
                "content": f"{SYSTEM_PROMPT_DYNAMIC_BOUNDARY}\n\n{dynamic_content}",
            })

        return result

    def build_for_api(self, tools: Optional[list[dict]] = None) -> tuple[list[dict], list[dict]]:
        """
        Build prompt for API call with tools.

        Returns:
            Tuple of (messages, tools)
        """
        prompt = self.build()

        if tools:
            # Insert tools at the end as a system message
            tools_content = self._format_tools(tools)
            prompt.append({"role": "system", "content": tools_content})

        return prompt, tools or []

    def _format_tools(self, tools: list[dict]) -> str:
        """Format tools as a string for system prompt."""
        if not tools:
            return ""

        lines = ["## Tools\n"]
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                lines.append(f"### {func.get('name', 'unknown')}")
                lines.append(func.get("description", ""))
                params = func.get("parameters", {})
                if params:
                    lines.append(f"Parameters: {params}")
                lines.append("")
            else:
                lines.append(f"### {tool.get('name', 'unknown')}")
                lines.append(tool.get("description", ""))
                lines.append("")

        return "\n".join(lines)

    @classmethod
    def from_messages(cls, messages: list[dict]) -> "SystemPromptBuilder":
        """Create builder from existing messages (for resume)."""
        builder = cls()
        for msg in messages:
            if msg.get("role") == "system":
                content = msg.get("content", "")
                if SYSTEM_PROMPT_DYNAMIC_BOUNDARY in content:
                    parts = content.split(SYSTEM_PROMPT_DYNAMIC_BOUNDARY)
                    builder.add_static(parts[0].strip())
                    if len(parts) > 1:
                        builder.add_dynamic(parts[1].strip())
                else:
                    builder.add_static(content)
        return builder


class StaticPromptSections:
    """
    Static prompt sections that are cached globally.

    These don't change between sessions and can be cached.
    """

    @staticmethod
    def intro() -> str:
        """Introduction section."""
        return """You are geocode, an AI coding assistant.

Your purpose is to help users write, edit, and understand code. You have access to tools for reading and writing files, executing shell commands, and more.

Guidelines:
- Be concise and helpful
- Ask clarifying questions when needed
- Explain your reasoning when helpful
- Focus on the user's task at hand"""

    @staticmethod
    def tool_usage() -> str:
        """Tool usage guidelines."""
        return """## Tool Usage

When using tools:
1. Use FileRead to view files before editing them
2. Use FileEdit for targeted text replacements (provide exact old_string)
3. Use FileWrite to create or overwrite files
4. Use Bash for shell commands (git, ls, grep, etc.)

For file operations:
- Always prefer FileRead first to see current content
- Use FileEdit for changes, not FileWrite (unless creating new files)
- Be careful with FileWrite as it overwrites existing content"""

    @staticmethod
    def bash_guidelines() -> str:
        """Bash tool guidelines."""
        return """## Bash Commands

Allowed commands include: git, ls, cat, grep, find, wc, head, tail, pwd, mkdir, rm, cp, mv, echo, touch, chmod, awk, sed, sort, uniq, diff, zip, unzip, tar, curl, wget, python, pip, npm, node, docker, make, cargo, go, java

Dangerous commands (rm -rf /, fork bombs, etc.) are blocked.

Always check the working directory before running commands that depend on paths."""

    @staticmethod
    def tone_and_style() -> str:
        """Tone and style guidelines."""
        return """## Tone and Style

- Be helpful, not pedantic
- Provide concrete examples when useful
- Suggest improvements, don't nitpick
- Use code blocks for code examples
- Be direct about limitations or uncertainties"""


class DynamicPromptSections:
    """
    Dynamic prompt sections that vary by session.

    These include memory context, project info, etc.
    """

    @staticmethod
    def memory_context(memory_entries: list[dict]) -> str:
        """Build memory context section."""
        if not memory_entries:
            return ""

        lines = ["## Relevant Memory\n"]
        for entry in memory_entries:
            lines.append(f"- {entry.get('content', '')}")

        return "\n".join(lines)

    @staticmethod
    def project_context(project_path: Optional[str] = None, git_info: Optional[dict] = None) -> str:
        """Build project context section."""
        if not project_path:
            return ""

        lines = ["## Project Context\n"]
        lines.append(f"Working directory: {project_path}")

        if git_info:
            if git_info.get("is_git"):
                lines.append(f"Git branch: {git_info.get('branch', 'unknown')}")

        return "\n".join(lines)

    @staticmethod
    def session_info(session_id: str) -> str:
        """Build session info section."""
        return f"""## Session

Session ID: {session_id}
This is a continuation of a previous conversation."""
