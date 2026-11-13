from typing import Any, Dict, List

from sdlc.algorithms.transcript_usage import TranscriptUsageHelper


class TranscriptLineFactory:
    """Builds raw transcript lines shaped like Claude Code writes them."""

    @staticmethod
    def assistant(message_id: str, at: str, output_tokens: int, tool: str = "", sidechain: bool = False,
                  model: str = "claude-sonnet-5-5") -> Dict[str, Any]:
        """Returns one assistant line of a request."""
        content: List[Dict[str, Any]] = [{"type": "text", "text": "x"}]
        if tool:
            content = [{"type": "tool_use", "id": f"{message_id}-{tool}", "name": tool, "input": {}}]
        return {
            "type": "assistant", "timestamp": at, "isSidechain": sidechain, "perTurnEffort": "high",
            "message": {"id": message_id, "model": model, "content": content,
                        "usage": {"input_tokens": 10, "output_tokens": output_tokens,
                                  "cache_creation_input_tokens": 100, "cache_read_input_tokens": 1000}},
        }


class TestTranscriptUsageHelper:
    """Covers request deduplication and aggregation."""

    def test_deduplicates_lines_of_one_request(self) -> None:
        """Merges the lines of one request, keeping the final usage and every tool call."""
        lines = [
            TranscriptLineFactory.assistant("m1", "2026-10-04T09:00:00.000Z", 5),
            TranscriptLineFactory.assistant("m1", "2026-10-04T09:00:01.000Z", 50, tool="Read"),
            TranscriptLineFactory.assistant("m1", "2026-10-04T09:00:01.000Z", 50, tool="Read"),
            TranscriptLineFactory.assistant("m2", "2026-10-04T09:00:05.000Z", 20, tool="Bash"),
            {"type": "user", "message": {"content": "hi"}},
        ]
        turns = TranscriptUsageHelper.turns(lines, include_sidechain=False)
        assert [turn.message_id for turn in turns] == ["m1", "m2"]
        assert turns[0].usage.output_tokens == 50 and turns[0].tool_names == ["Read"]
        assert turns[0].effort == "high"

    def test_skips_sidechain_and_synthetic(self) -> None:
        """Skips sidechain lines unless asked and always skips synthetic messages."""
        lines = [
            TranscriptLineFactory.assistant("m1", "t", 5, sidechain=True),
            TranscriptLineFactory.assistant("m2", "t", 5, model="<synthetic>"),
        ]
        assert TranscriptUsageHelper.turns(lines, include_sidechain=False) == []
        assert len(TranscriptUsageHelper.turns(lines, include_sidechain=True)) == 1

    def test_summarizes_turns(self) -> None:
        """Sums usage and counts tool calls, models, and the time span."""
        lines = [
            TranscriptLineFactory.assistant("m1", "2026-10-04T09:00:00.000Z", 10, tool="Read"),
            TranscriptLineFactory.assistant("m2", "2026-10-04T09:01:00.000Z", 20, tool="Read"),
        ]
        summary = TranscriptUsageHelper.summarize(TranscriptUsageHelper.turns(lines, include_sidechain=True))
        assert summary.api_calls == 2
        assert summary.usage.output_tokens == 30
        assert summary.usage.total_tokens == 2 * (10 + 100 + 1000) + 30
        assert summary.tool_calls == {"Read": 2}
        assert (summary.started_at, summary.ended_at) == ("2026-10-04T09:00:00.000Z", "2026-10-04T09:01:00.000Z")
