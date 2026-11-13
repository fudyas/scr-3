from pathlib import Path
from typing import Optional


class DraftSource:
    """Owns the host-local drafts of one document kind, such as plans or reviews, before they land on the ledger."""

    def __init__(self, drafts_dir: Path, file_name: str) -> None:
        """Initializes the source.

        Args:
            drafts_dir: the directory that holds one `<ITEM>/<file name>` draft per item.
            file_name: the draft file name, such as `PLAN.md` or `REVIEW.md`.
        """
        self._drafts_dir = drafts_dir
        self._file_name = file_name

    def path(self, item_id: str) -> Path:
        """Returns the draft path for the item."""
        return self._drafts_dir / item_id / self._file_name

    def read(self, item_id: str) -> Optional[str]:
        """Returns the draft text, or None when no draft exists."""
        path = self.path(item_id)
        return path.read_text(encoding="utf-8") if path.exists() else None

    def write(self, item_id: str, text: str) -> Path:
        """Writes the draft and returns its path."""
        path = self.path(item_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def discard(self, item_id: str) -> None:
        """Removes the draft after it lands on the ledger."""
        path = self.path(item_id)
        if path.exists():
            path.unlink()
        if path.parent.exists() and not any(path.parent.iterdir()):
            path.parent.rmdir()
