"""FileRead tool - read files from disk."""

import asyncio
from pathlib import Path
from typing import Optional

from pydantic import Field

from geoffrey_llm.geocode.tools.base import Tool, ToolInput, ToolResult


class FileReadInput(ToolInput):
    """Input schema for FileRead tool."""

    file_path: str = Field(..., description="The absolute path to the file to read")
    offset: int = Field(default=0, description="Line offset to start reading from")
    limit: int = Field(default=1000, description="Maximum number of lines to read")
    show_line_numbers: bool = Field(default=True, description="Include line numbers in output")


class FileReadTool(Tool):
    """
    Tool for reading files from the filesystem.

    Supports:
    - Partial reads with offset/limit
    - Line numbers in output
    - Async file operations
    """

    @property
    def name(self) -> str:
        return "FileRead"

    @property
    def description(self) -> str:
        return "Read the contents of a file from the filesystem. Use this to view code files, configuration, or other text files."

    def input_schema(self) -> type[ToolInput]:
        return FileReadInput

    async def call(self, input_data: FileReadInput) -> ToolResult:
        """Read file contents."""
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

            # Read file content
            content = await asyncio.to_thread(self._read_file, file_path, input_data.offset, input_data.limit)

            if content:
                if input_data.show_line_numbers:
                    lines = content.split("\n")
                    numbered_lines = [
                        f"{i + input_data.offset + 1:6d}  {line}"
                        for i, line in enumerate(lines)
                    ]
                    content = "\n".join(numbered_lines)

            return ToolResult(success=True, output=content)

        except PermissionError:
            return ToolResult(success=False, error=f"Permission denied: {input_data.file_path}")
        except Exception as e:
            return ToolResult(success=False, error=f"Error reading file: {str(e)}")

    def _read_file(self, path: Path, offset: int, limit: int) -> str:
        """Synchronous file read with offset/limit."""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            # Seek to offset (line based)
            for _ in range(offset):
                f.readline()

            # Read up to limit lines
            lines = []
            for i, line in enumerate(f):
                if i >= limit:
                    break
                lines.append(line.rstrip("\n\r"))

            return "\n".join(lines)
