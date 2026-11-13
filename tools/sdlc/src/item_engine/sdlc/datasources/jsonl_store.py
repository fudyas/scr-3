import fcntl
import json
from pathlib import Path
from typing import Any, Dict, Iterator, Optional


class JsonlStore:
    """Appends and reads JSON-lines streams and per-key cursors in one local directory."""

    def __init__(self, directory: Path) -> None:
        """Initializes the store.

        Args:
            directory: the directory that holds `<stream>.jsonl` files and the `cursors/` folder.
        """
        self._directory = directory

    @property
    def directory(self) -> Path:
        """Returns the directory that holds the streams."""
        return self._directory

    def append(self, stream: str, record: Dict[str, Any]) -> None:
        """Appends one record to the stream under an exclusive file lock."""
        self._directory.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n"
        with open(self._stream_path(stream), "a", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.write(line)
            fcntl.flock(handle, fcntl.LOCK_UN)

    def read(self, stream: str) -> Iterator[Dict[str, Any]]:
        """Yields every well-formed record of the stream; a torn line is skipped."""
        path = self._stream_path(stream)
        if not path.exists():
            return
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def cursor(self, key: str) -> Optional[Dict[str, Any]]:
        """Returns the stored cursor for the key, or None."""
        path = self._cursor_path(key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def set_cursor(self, key: str, value: Dict[str, Any]) -> None:
        """Stores the cursor for the key with an atomic replace."""
        path = self._cursor_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value), encoding="utf-8")
        temporary.replace(path)

    def _stream_path(self, stream: str) -> Path:
        """Returns the file of the stream."""
        return self._directory / f"{stream}.jsonl"

    def _cursor_path(self, key: str) -> Path:
        """Returns the file of the cursor."""
        safe_key = "".join(character if character.isalnum() or character in "-_" else "_" for character in key)
        return self._directory / "cursors" / f"{safe_key}.json"
