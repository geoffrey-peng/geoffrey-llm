"""History management for REPL."""

import os
from pathlib import Path
from typing import Optional

try:
    from prompt_toolkit.history import FileHistory
except ImportError:
    FileHistory = None  # type: ignore


class History:
    """
    Command history management.

    Persists command history to a file.
    """

    def __init__(self, history_file: Optional[Path] = None):
        if history_file is None:
            # Default to ~/.geoffrey/history
            home = Path.home()
            geoffrey_dir = home / ".geoffrey"
            geoffrey_dir.mkdir(exist_ok=True)
            history_file = geoffrey_dir / "history"

        self.history_file = history_file
        self._history: list[str] = []
        self._load()

    def _load(self):
        """Load history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self._history = [line.strip() for line in f if line.strip()]
            except Exception:
                self._history = []

    def _save(self):
        """Save history to file."""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                for line in self._history[-1000:]:  # Keep last 1000 entries
                    f.write(line + "\n")
        except Exception:
            pass

    def add(self, command: str):
        """Add a command to history."""
        if command.strip() and command != self._history[-1] if self._history else True:
            self._history.append(command)
            self._save()

    def get_history(self) -> list[str]:
        """Get all history entries."""
        return self._history.copy()

    def search(self, query: str) -> list[str]:
        """Search history for entries containing query."""
        return [h for h in self._history if query.lower() in h.lower()]

    def clear(self):
        """Clear all history."""
        self._history = []
        self._save()

    def get_prompt_toolkit_history(self):
        """Get prompt_toolkit compatible history object."""
        if FileHistory is None:
            return None
        return FileHistory(str(self.history_file))
