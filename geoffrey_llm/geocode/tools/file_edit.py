"""FileEdit tool - edit files using search/replace."""

import asyncio
import re
from pathlib import Path
from typing import Optional

from pydantic import Field

from geoffrey_llm.geocode.tools.base import Tool, ToolInput, ToolResult


class FileEditInput(ToolInput):
    """Input schema for FileEdit tool."""

    file_path: str = Field(..., description="The absolute path to the file to edit")
    old_string: str = Field(..., description="The exact string to find and replace")
    new_string: str = Field(..., description="The replacement string")
    dry_run: bool = Field(default=False, description="Show what would change without making edits")


class FileEditTool(Tool):
    """
    Tool for editing files using search/replace.

    Replaces exact old_string with new_string in the file.
    Useful for making targeted edits to code or text files.
    """

    @property
    def name(self) -> str:
        return "FileEdit"

    @property
    def description(self) -> str:
        return "Edit a file by replacing exact text. Takes old_string (what to find) and new_string (replacement). Use for targeted code edits."

    def input_schema(self) -> type[ToolInput]:
        return FileEditInput

    async def call(self, input_data: FileEditInput) -> ToolResult:
        """Edit file using search/replace."""
        try:
            file_path = Path(input_data.file_path)

            if not file_path.exists():
                return ToolResult(
                    success=False,
                    error=f"File not found: {file_path}",
                )

            if not file_path.is_file():
                return ToolResult(
                    success=False,
                    error=f"Not a file: {file_path}",
                )

            # Read current content
            def _read():
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()

            content = await asyncio.to_thread(_read)

            # Check if old_string exists
            if input_data.old_string not in content:
                return ToolResult(
                    success=False,
                    error=f"old_string not found in file. Please check the exact text to replace.",
                )

            if input_data.dry_run:
                # Show what would change
                new_content = content.replace(input_data.old_string, input_data.new_string, 1)
                diff = self._show_diff(content, new_content)
                return ToolResult(
                    success=True,
                    output=f"DRY RUN - Would make this change:\n{diff}",
                )

            # Perform the edit
            new_content = content.replace(input_data.old_string, input_data.new_string, 1)

            def _write():
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)

            await asyncio.to_thread(_write)

            return ToolResult(
                success=True,
                output=f"Successfully edited {file_path}",
            )

        except PermissionError:
            return ToolResult(
                success=False,
                error=f"Permission denied: {input_data.file_path}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error editing file: {str(e)}",
            )

    def _show_diff(self, old: str, new: str) -> str:
        """Show a simple unified diff."""
        old_lines = old.split("\n")
        new_lines = new.split("\n")

        # Find the first difference
        i = 0
        for i, (o, n) in enumerate(zip(old_lines, new_lines)):
            if o != n:
                break

        # Show context
        context = 3
        start = max(0, i - context)
        end = min(len(new_lines), i + context + 3)

        diff_lines = []
        diff_lines.append("--- (original)")
        diff_lines.append("+++ (proposed)")
        diff_lines.append(f"@@ -{i + 1},{end - start} +{i + 1},{end - start} @@")

        for j in range(start, end):
            if j < len(old_lines) and j < len(new_lines):
                if old_lines[j] == new_lines[j]:
                    diff_lines.append(f" {old_lines[j]}")
                else:
                    if j < len(old_lines):
                        diff_lines.append(f"-{old_lines[j]}")
                    if j < len(new_lines):
                        diff_lines.append(f"+{new_lines[j]}")
            elif j < len(old_lines):
                diff_lines.append(f"-{old_lines[j]}")
            else:
                diff_lines.append(f"+{new_lines[j]}")

        return "\n".join(diff_lines)
