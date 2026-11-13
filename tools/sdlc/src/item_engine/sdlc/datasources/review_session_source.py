import os
import tempfile
from pathlib import Path
from typing import Optional

from sdlc.models.review_session import ReviewSession


class ReviewSessionSource:
    """Stores review context atomically in the main checkout's host-local logs directory."""

    def __init__(self, logs_dir: Path) -> None:
        """Initializes the source with the directory that holds per-item logs."""
        self._logs_dir = logs_dir

    def read(self, item_id: str) -> Optional[ReviewSession]:
        """Returns the persisted review context, or None before presentation."""
        path = self._logs_dir / item_id / "review-context.json"
        return ReviewSession.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None

    def write(self, session: ReviewSession) -> ReviewSession:
        """Replaces the context atomically and returns the stored session.

        Args:
            session: the workspace and verification state to persist.

        Returns:
            The stored context.
        """

        # Writes beside the destination so replacement stays on the same filesystem
        directory = self._logs_dir / session.item_id
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(session.model_dump_json(indent=2))
        try:
            os.replace(temporary, directory / "review-context.json")
        finally:
            temporary.unlink(missing_ok=True)
        return session
