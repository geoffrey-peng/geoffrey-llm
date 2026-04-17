"""Session management for geocode."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from geoffrey_llm.geocode.session.state import Session, load_session, save_session


class SessionManager:
    """
    Manages conversation sessions.

    Sessions are stored as JSON files in ~/.geoffrey/sessions/
    """

    def __init__(self, sessions_dir: Optional[Path] = None):
        if sessions_dir is None:
            home = Path.home()
            geoffrey_dir = home / ".geoffrey"
            sessions_dir = geoffrey_dir / "sessions"

        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        self._sessions: dict[str, Session] = {}
        self._load_existing()

    def _load_existing(self):
        """Load existing sessions from disk."""
        for file_path in self.sessions_dir.glob("*.json"):
            session = load_session(file_path)
            if session:
                self._sessions[session.id] = session

    def _get_session_path(self, session_id: str) -> Path:
        """Get the file path for a session."""
        return self.sessions_dir / f"{session_id}.json"

    def _generate_id(self) -> str:
        """Generate a unique session ID."""
        return f"sess_{uuid.uuid4().hex[:12]}"

    def create(self, project_path: Optional[str] = None) -> Session:
        """
        Create a new session.

        Args:
            project_path: Optional project directory path

        Returns:
            The new Session object
        """
        session_id = self._generate_id()
        project_hash = None

        if project_path:
            # Generate project hash
            import hashlib
            project_hash = f"proj_{hashlib.md5(project_path.encode()).hexdigest()[:12]}"

        session = Session(
            id=session_id,
            created_at=datetime.now(),
            last_active=datetime.now(),
            project_path=project_path,
            project_hash=project_hash,
            messages=[],
            metadata={},
        )

        self._sessions[session_id] = session
        self.save(session)

        return session

    def resume(self, session_id: str) -> Optional[Session]:
        """
        Resume an existing session.

        Args:
            session_id: The session ID to resume

        Returns:
            The Session object if found, None otherwise
        """
        session = self._sessions.get(session_id)
        if session:
            session.last_active = datetime.now()
            self.save(session)
        return session

    def list(self) -> list[Session]:
        """
        List all sessions sorted by last_active (most recent first).

        Returns:
            List of Session objects
        """
        sessions = list(self._sessions.values())
        return sorted(sessions, key=lambda s: s.last_active, reverse=True)

    def delete(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session ID to delete

        Returns:
            True if deleted, False if not found
        """
        if session_id not in self._sessions:
            return False

        del self._sessions[session_id]

        # Delete the file
        file_path = self._get_session_path(session_id)
        if file_path.exists():
            file_path.unlink()

        return True

    def save(self, session: Session) -> None:
        """
        Save a session to disk.

        Args:
            session: The session to save
        """
        file_path = self._get_session_path(session.id)
        save_session(session, file_path)

    def get(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID without updating last_active.

        Args:
            session_id: The session ID

        Returns:
            The Session object if found, None otherwise
        """
        return self._sessions.get(session_id)

    def count(self) -> int:
        """Get the total number of sessions."""
        return len(self._sessions)

    def cleanup_old(self, keep_last: int = 10) -> int:
        """
        Delete old sessions, keeping only the most recent ones.

        Args:
            keep_last: Number of recent sessions to keep

        Returns:
            Number of sessions deleted
        """
        sessions = self.list()
        deleted = 0

        for session in sessions[keep_last:]:
            if self.delete(session.id):
                deleted += 1

        return deleted
