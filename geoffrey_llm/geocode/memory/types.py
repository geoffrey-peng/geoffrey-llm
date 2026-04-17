"""Memory types for geocode memory system."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Types of memories that can be stored."""

    USER = "user"           # User preferences, identity, background
    FEEDBACK = "feedback"   # User corrections, preferences, feedback
    PROJECT = "project"      # Project-specific context, decisions
    REFERENCE = "reference"  # External reference material, documentation


class MemoryEntry(BaseModel):
    """
    A single memory entry with YAML frontmatter.

    Stored as:
    ---
    id: mem_abc123
    type: user
    created_at: 2026-04-18T10:00:00Z
    updated_at: 2026-04-18T10:00:00Z
    tags:
      - preference
      - coding
    project: null
    ---
    Memory content here.
    """

    id: str
    type: MemoryType
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    tags: list[str] = Field(default_factory=list)
    project: Optional[str] = None  # Project hash if project-specific
    content: str = ""


class MemoryFrontmatter(BaseModel):
    """YAML frontmatter for memory files."""

    id: str
    type: MemoryType
    created_at: str
    updated_at: str
    tags: list[str] = []
    project: Optional[str] = None


def format_memory_file(entry: MemoryEntry) -> str:
    """
    Format a memory entry as a YAML-frontmatter markdown file.

    Returns content like:
    ---
    id: mem_abc123
    type: user
    created_at: 2026-04-18T10:00:00Z
    updated_at: 2026-04-18T10:00:00Z
    tags:
      - preference
    project: null
    ---
    Memory content here.
    """
    lines = ["---"]
    lines.append(f"id: {entry.id}")
    lines.append(f"type: {entry.type.value}")
    lines.append(f"created_at: {entry.created_at.isoformat()}Z")
    lines.append(f"updated_at: {entry.updated_at.isoformat()}Z")

    if entry.tags:
        lines.append("tags:")
        for tag in entry.tags:
            lines.append(f"  - {tag}")

    if entry.project:
        lines.append(f"project: {entry.project}")
    else:
        lines.append("project: null")

    lines.append("---")
    lines.append("")  # Blank line after frontmatter
    lines.append(entry.content)

    return "\n".join(lines)


def parse_memory_file(content: str) -> MemoryEntry:
    """
    Parse a memory file with YAML frontmatter.

    Returns a MemoryEntry with parsed metadata and content.
    """
    from geoffrey_llm.geocode.memory.yaml_frontmatter import parse_frontmatter

    metadata, body = parse_frontmatter(content)

    # Parse datetime strings
    created_at = datetime.fromisoformat(metadata.created_at.replace("Z", "+00:00"))
    updated_at = datetime.fromisoformat(metadata.updated_at.replace("Z", "+00:00"))

    return MemoryEntry(
        id=metadata.id,
        type=MemoryType(metadata.type),
        created_at=created_at,
        updated_at=updated_at,
        tags=metadata.tags,
        project=metadata.project,
        content=body.strip(),
    )
