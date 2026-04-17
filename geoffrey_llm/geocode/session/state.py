"""Session state management for geocode."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Session:
    """
    A conversation session.

    Sessions persist conversation history and metadata.
    """
    id: str
    created_at: datetime
    last_active: datetime
    project_path: Optional[str] = None
    project_hash: Optional[str] = None
    messages: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() + "Z",
            "last_active": self.last_active.isoformat() + "Z",
            "project_path": self.project_path,
            "project_hash": self.project_hash,
            "messages": self.messages,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Create from dictionary."""
        created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        last_active = datetime.fromisoformat(data["last_active"].replace("Z", "+00:00"))

        return cls(
            id=data["id"],
            created_at=created_at,
            last_active=last_active,
            project_path=data.get("project_path"),
            project_hash=data.get("project_hash"),
            messages=data.get("messages", []),
            metadata=data.get("metadata", {}),
        )


def load_session(file_path: Path) -> Optional[Session]:
    """Load a session from a JSON file."""
    if not file_path.exists():
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Session.from_dict(data)
    except Exception:
        return None


def save_session(session: Session, file_path: Path) -> None:
    """Save a session to a JSON file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
