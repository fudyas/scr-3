from abc import ABC
from typing import Any, Dict, Iterable, List, Set

from sdlc.models.telemetry import TokenUsage, TranscriptTurn, UsageSummary

# Model name Claude Code writes on locally generated messages that cost no tokens
SYNTHETIC_MODEL = "<synthetic>"


class TranscriptUsageHelper(ABC):
    """Turns raw Claude Code transcript lines into deduplicated model requests."""

    @staticmethod
    def turns(lines: Iterable[Dict[str, Any]], include_sidechain: bool) -> List[TranscriptTurn]:
        """Returns one turn per model request, in first-seen order.

        Steps:
            1. Keep only assistant lines; skip sidechain lines unless asked for them.
            2. Group lines by `message.id`, because one request spans several lines.
            3. Keep the largest usage seen per request and every distinct tool call.

        Args:
            lines: parsed transcript lines.
            include_sidechain: whether to keep lines a subagent wrote into this transcript.

        Returns:
            The deduplicated turns.
        """
        turns: Dict[str, TranscriptTurn] = {}
        seen_tool_ids: Dict[str, Set[str]] = {}
        for line in lines:
            if line.get("type") != "assistant":
                continue
            if line.get("isSidechain") and not include_sidechain:
                continue
            message = line.get("message") or {}
            message_id = message.get("id")
            model = message.get("model")
            if not message_id or model == SYNTHETIC_MODEL:
                continue

            # Starts a turn on the first line of a request
            turn = turns.get(message_id)
            if turn is None:
                turn = TranscriptTurn(
                    message_id=message_id,
                    at=line.get("timestamp", ""),
                    model=model,
                    effort=line.get("perTurnEffort"),
                )
                turns[message_id] = turn
                seen_tool_ids[message_id] = set()

            # Keeps the most complete usage, since later lines carry the final output count
            usage = TranscriptUsageHelper._usage(message.get("usage") or {})
            if usage.total_tokens >= turn.usage.total_tokens:
                turn.usage = usage

            # Collects each tool call once
            for block in message.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_id = block.get("id") or f"{block.get('name')}-{len(turn.tool_names)}"
                    if tool_id not in seen_tool_ids[message_id]:
                        seen_tool_ids[message_id].add(tool_id)
                        turn.tool_names.append(block.get("name", "unknown"))
        return list(turns.values())

    @staticmethod
    def summarize(turns: List[TranscriptTurn]) -> UsageSummary:
        """Returns the aggregate usage, models, efforts, and tool calls of the turns."""
        summary = UsageSummary()
        for turn in turns:
            summary.api_calls += 1
            summary.usage.input_tokens += turn.usage.input_tokens
            summary.usage.output_tokens += turn.usage.output_tokens
            summary.usage.cache_creation_tokens += turn.usage.cache_creation_tokens
            summary.usage.cache_read_tokens += turn.usage.cache_read_tokens
            if turn.model and turn.model not in summary.models:
                summary.models.append(turn.model)
            if turn.effort and turn.effort not in summary.efforts:
                summary.efforts.append(turn.effort)
            for tool_name in turn.tool_names:
                summary.tool_calls[tool_name] = summary.tool_calls.get(tool_name, 0) + 1
            if turn.at and (summary.started_at is None or turn.at < summary.started_at):
                summary.started_at = turn.at
            if turn.at and (summary.ended_at is None or turn.at > summary.ended_at):
                summary.ended_at = turn.at
        return summary

    @staticmethod
    def _usage(raw: Dict[str, Any]) -> TokenUsage:
        """Returns the token usage read from a raw `message.usage` object."""
        return TokenUsage(
            input_tokens=int(raw.get("input_tokens") or 0),
            output_tokens=int(raw.get("output_tokens") or 0),
            cache_creation_tokens=int(raw.get("cache_creation_input_tokens") or 0),
            cache_read_tokens=int(raw.get("cache_read_input_tokens") or 0),
        )
