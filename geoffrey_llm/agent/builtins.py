"""Convenience access to geocode's built-in file/shell tools for agents."""

from geoffrey_llm.geocode.tools.base import Tool
from geoffrey_llm.geocode.tools.file_read import FileReadTool
from geoffrey_llm.geocode.tools.file_write import FileWriteTool
from geoffrey_llm.geocode.tools.file_edit import FileEditTool
from geoffrey_llm.geocode.tools.bash import BashTool


def default_tools() -> list[Tool]:
    """Fresh instances of the geocode built-ins: FileRead / FileWrite / FileEdit / Bash."""
    return [FileReadTool(), FileWriteTool(), FileEditTool(), BashTool()]
