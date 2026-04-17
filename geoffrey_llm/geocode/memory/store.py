"""File-based memory storage for geocode."""

import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from geoffrey_llm.geocode.memory.types import (
    MemoryEntry,
    MemoryType,
    format_memory_file,
    parse_memory_file,
)


class MemoryStore:
    """
    File-based memory storage.

    Memories are stored as markdown files with YAML frontmatter in:
    ~/.geoffrey/memory/{type}/{id}.md

    Supports:
    - CRUD operations on memories
    - Query by type and tags
    - Project-specific memory isolation
    - MEMORY.md index generation
    """

    def __init__(self, memory_dir: Optional[Path] = None):
        if memory_dir is None:
            # Default to ~/.geoffrey/memory
            home = Path.home()
            geoffrey_dir = home / ".geoffrey"
            memory_dir = geoffrey_dir / "memory"

        self.memory_dir = Path(memory_dir)
        self._ensure_directories()

    def _ensure_directories(self):
        """Create memory directories if they don't exist."""
        for memory_type in MemoryType:
            type_dir = self.memory_dir / memory_type.value
            type_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, memory_id: str, memory_type: MemoryType) -> Path:
        """Get the file path for a memory."""
        return self.memory_dir / memory_type.value / f"{memory_id}.md"

    def _generate_id(self) -> str:
        """Generate a unique memory ID."""
        return f"mem_{uuid.uuid4().hex[:12]}"

    async def save(self, entry: MemoryEntry) -> MemoryEntry:
        """
        Save a memory entry to disk.

        If entry.id is None, generates a new ID.
        """
        if not entry.id:
            entry.id = self._generate_id()
            entry.created_at = datetime.now()
        entry.updated_at = datetime.now()

        file_path = self._get_file_path(entry.id, entry.type)
        content = format_memory_file(entry)

        # Write to disk
        def _write():
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        import asyncio
        await asyncio.to_thread(_write)

        # Update index
        await self.update_index()

        return entry

    async def load(self, memory_id: str, memory_type: MemoryType) -> Optional[MemoryEntry]:
        """
        Load a memory entry by ID and type.
        """
        file_path = self._get_file_path(memory_id, memory_type)

        if not file_path.exists():
            return None

        def _read():
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        import asyncio
        content = await asyncio.to_thread(_read)

        try:
            return parse_memory_file(content)
        except Exception:
            return None

    async def query(
        self,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[list[str]] = None,
        project: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[MemoryEntry]:
        """
        Query memories by type, tags, project, or full-text search.

        Args:
            memory_type: Filter by memory type
            tags: Filter by tags (AND logic)
            project: Filter by project hash
            search: Full-text search in content

        Returns:
            List of matching MemoryEntry objects
        """
        results = []

        # Determine which directories to scan
        if memory_type:
            types_to_scan = [memory_type]
        else:
            types_to_scan = list(MemoryType)

        for mt in types_to_scan:
            type_dir = self.memory_dir / mt.value
            if not type_dir.exists():
                continue

            # Scan all .md files in the type directory
            for file_path in type_dir.glob("*.md"):
                try:
                    def _read():
                        with open(file_path, "r", encoding="utf-8") as f:
                            return f.read()

                    import asyncio
                    content = await asyncio.to_thread(_read)
                    entry = parse_memory_file(content)

                    # Apply filters
                    if tags and not all(tag in entry.tags for tag in tags):
                        continue
                    if project and entry.project != project:
                        continue
                    if search and search.lower() not in entry.content.lower():
                        continue

                    results.append(entry)

                except Exception:
                    # Skip invalid memory files
                    continue

        return results

    async def delete(self, memory_id: str, memory_type: MemoryType) -> bool:
        """
        Delete a memory entry.

        Returns:
            True if deleted, False if not found
        """
        file_path = self._get_file_path(memory_id, memory_type)

        if not file_path.exists():
            return False

        def _delete():
            file_path.unlink()

        import asyncio
        await asyncio.to_thread(_delete)

        # Update index
        await self.update_index()

        return True

    async def update_index(self):
        """
        Regenerate MEMORY.md index file.

        Lists all memories with one-line descriptions.
        """
        index_path = self.memory_dir / "MEMORY.md"

        lines = ["# Memory Index\n"]
        lines.append(f"\nLast updated: {datetime.now().isoformat()}Z\n")

        all_entries = await self.query()

        # Group by type
        by_type: dict[MemoryType, list[MemoryEntry]] = {}
        for entry in all_entries:
            if entry.type not in by_type:
                by_type[entry.type] = []
            by_type[entry.type].append(entry)

        # Write sections
        for memory_type in MemoryType:
            entries = by_type.get(memory_type, [])
            if not entries:
                continue

            lines.append(f"## {memory_type.value.capitalize()}\n")
            for entry in entries:
                # First line of content as description
                first_line = entry.content.split("\n")[0][:60]
                desc = f"{first_line}..." if len(entry.content.split("\n")) > 1 else first_line
                lines.append(f"- [{entry.id}]({memory_type.value}/{entry.id}.md) - {desc}")
            lines.append("")

        def _write():
            with open(index_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

        import asyncio
        await asyncio.to_thread(_write)

    def get_memory_dir(self) -> Path:
        """Get the memory directory path."""
        return self.memory_dir


def get_project_hash(project_path: Optional[Path] = None) -> str:
    """
    Generate a stable hash for a project directory.

    Used for project-specific memory isolation.
    """
    if project_path is None:
        import os
        project_path = Path(os.getcwd())

    # Use the git root if available, otherwise use the path itself
    git_dir = project_path / ".git"
    if git_dir.exists():
        # Hash the git root path for consistency
        hash_input = str(project_path.resolve())
    else:
        hash_input = str(project_path.resolve())

    return f"proj_{hashlib.md5(hash_input.encode()).hexdigest()[:12]}"
