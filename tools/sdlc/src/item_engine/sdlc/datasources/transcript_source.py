import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from sdlc.models.transcript import TranscriptChunk


class TranscriptSource:
    """Reads Claude Code session and subagent transcripts; the only code that knows their layout."""

    def __init__(self, projects_dir: Path) -> None:
        """Initializes the source.

        Args:
            projects_dir: the Claude Code projects directory, usually `~/.codex/projects`.
        """
        self._projects_dir = projects_dir

    def exists(self, transcript_path: Path) -> bool:
        """Returns whether the transcript file exists."""
        return transcript_path.exists()

    def read_from(self, transcript_path: Path, offset: int) -> TranscriptChunk:
        """Returns the complete lines written after the byte offset.

        Args:
            transcript_path: the JSONL transcript file.
            offset: the byte offset where the previous read stopped.

        Returns:
            The parsed lines and the offset after the last complete line.
        """
        if not transcript_path.exists():
            return TranscriptChunk(lines=[], next_offset=offset)
        with open(transcript_path, "rb") as handle:
            handle.seek(offset)
            data = handle.read()

        # Stops at the last newline so a line still being written is read next time
        complete_end = data.rfind(b"\n") + 1
        lines: List[Dict[str, Any]] = []
        for raw_line in data[:complete_end].splitlines():
            try:
                lines.append(json.loads(raw_line))
            except json.JSONDecodeError:
                continue
        return TranscriptChunk(lines=lines, next_offset=offset + complete_end)

    def read_all(self, transcript_path: Path) -> List[Dict[str, Any]]:
        """Returns every complete line of the transcript."""
        return self.read_from(transcript_path, 0).lines

    def subagent_meta(self, transcript_path: Path) -> Dict[str, Any]:
        """Returns the launch metadata stored beside a subagent transcript, or an empty mapping."""
        meta_path = transcript_path.with_suffix(".meta.json")
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def session_transcripts(self, project_dir_name: Optional[str]) -> Iterator[Path]:
        """Yields every main-session transcript of one project, or of all projects.

        Args:
            project_dir_name: the encoded project folder name; None scans every project.
        """
        roots = [self._projects_dir / project_dir_name] if project_dir_name else sorted(self._projects_dir.glob("*"))
        for root in roots:
            yield from sorted(root.glob("*.jsonl"))

    def subagent_transcripts(self, session_transcript: Path) -> Iterator[Path]:
        """Yields the subagent transcripts that belong to a main-session transcript."""
        subagents_dir = session_transcript.with_suffix("") / "subagents"
        yield from sorted(subagents_dir.glob("agent-*.jsonl"))

    @staticmethod
    def project_dir_name(project_dir: Path) -> str:
        """Returns the folder name Claude Code uses for a project directory."""
        return "".join(character if character.isalnum() else "-" for character in str(project_dir))
