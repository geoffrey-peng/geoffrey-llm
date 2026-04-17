"""FileWrite tool - write files to disk."""

import asyncio
from pathlib import Path

from pydantic import Field

from geoffrey_llm.geocode.tools.base import Tool, ToolInput, ToolResult


class FileWriteInput(ToolInput):
    """Input schema for FileWrite tool."""

    file_path: str = Field(..., description="The absolute path to the file to write")
    content: str = Field(..., description="The content to write to the file")
    append: bool = Field(default=False, description="Append to existing file instead of overwriting")


class FileWriteTool(Tool):
    """
    Tool for writing files to the filesystem.

    Supports:
    - Create new files
    - Overwrite existing files
    - Append to existing files
    """

    @property
    def name(self) -> str:
        return "FileWrite"

    @property
    def description(self) -> str:
        return "Write content to a file. Creates a new file or overwrites an existing one. Use append=true to add to existing files."

    def input_schema(self) -> type[ToolInput]:
        return FileWriteInput

    async def call(self, input_data: FileWriteInput) -> ToolResult:
        """Write content to file."""
        try:
            file_path = Path(input_data.file_path)

            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            mode = "a" if input_data.append else "w"

            def _write():
                with open(file_path, mode, encoding="utf-8") as f:
                    f.write(input_data.content)

            await asyncio.to_thread(_write)

            action = "appended to" if input_data.append else "written to"
            return ToolResult(
                success=True,
                output=f"Successfully {action} {file_path}",
            )

        except PermissionError:
            return ToolResult(
                success=False,
                error=f"Permission denied: {input_data.file_path}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error writing file: {str(e)}",
            )
