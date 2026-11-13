from typing import Any, Dict, List

from primitives.models.strict_model import StrictModel



class TranscriptChunk(StrictModel):
    """Transcript lines read from a byte offset, with the offset to resume from."""

    # Lists the parsed transcript lines
    lines: List[Dict[str, Any]]

    # Gives the byte offset where the next read resumes
    next_offset: int
