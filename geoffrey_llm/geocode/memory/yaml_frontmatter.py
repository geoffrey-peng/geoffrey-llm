"""YAML frontmatter parsing for memory files."""

import re
from typing import Optional, Tuple

from geoffrey_llm.geocode.memory.types import MemoryFrontmatter


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)


def parse_frontmatter(content: str) -> Tuple[MemoryFrontmatter, str]:
    """
    Parse YAML frontmatter from markdown content.

    Args:
        content: Full file content with frontmatter

    Returns:
        Tuple of (frontmatter metadata, body content)
    """
    match = FRONTMATTER_RE.match(content)
    if not match:
        raise ValueError("Invalid frontmatter format: missing --- delimiters")

    yaml_str = match.group(1)
    body = match.group(2)

    # Parse YAML manually (simple parser for our format)
    metadata = _parse_yaml(yaml_str)

    return metadata, body


def _parse_yaml(yaml_str: str) -> MemoryFrontmatter:
    """
    Simple YAML parser for memory frontmatter.

    Handles our specific format:
    - Simple key: value pairs
    - Lists with - prefix
    - Null values
    """
    lines = yaml_str.split("\n")
    data = {}
    current_list: Optional[str] = None
    current_list_values: list = []

    for line in lines:
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        # Check for list item
        if stripped.startswith("- "):
            if current_list:
                data[current_list] = current_list_values
            current_list_values.append(stripped[2:])
            continue

        # End of list
        if current_list and not stripped.startswith("-"):
            data[current_list] = current_list_values
            current_list = None
            current_list_values = []

        # Key-value pair
        if ": " in stripped:
            key, value = stripped.split(": ", 1)
            if value == "null" or value == "":
                value = None
            elif value.startswith("[") and value.endswith("]"):
                # List reference - will be filled by list items
                current_list = key
                current_list_values = []
                continue
            data[key] = value
        elif stripped.endswith(":"):
            # Start of list
            current_list = stripped[:-1]
            current_list_values = []

    # Close any open list
    if current_list:
        data[current_list] = current_list_values

    return MemoryFrontmatter(
        id=data.get("id", ""),
        type=data.get("type", "user"),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
        tags=data.get("tags", []),
        project=data.get("project"),
    )


def create_frontmatter(
    id: str,
    type: str,
    created_at: str,
    updated_at: str,
    tags: list[str],
    project: Optional[str] = None,
) -> str:
    """
    Create YAML frontmatter string.

    Args:
        id: Memory ID
        type: Memory type
        created_at: ISO datetime string
        updated_at: ISO datetime string
        tags: List of tags
        project: Optional project hash

    Returns:
        YAML frontmatter string
    """
    lines = [
        f"id: {id}",
        f"type: {type}",
        f"created_at: {created_at}",
        f"updated_at: {updated_at}",
    ]

    if tags:
        lines.append("tags:")
        for tag in tags:
            lines.append(f"  - {tag}")

    if project:
        lines.append(f"project: {project}")
    else:
        lines.append("project: null")

    return "---\n" + "\n".join(lines) + "\n---"
