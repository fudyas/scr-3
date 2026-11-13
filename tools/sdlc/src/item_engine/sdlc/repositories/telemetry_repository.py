import json
import sqlite3
from typing import Any, Callable, Dict, List, Optional

from sdlc.algorithms.timestamps import TimestampHelper
from sdlc.datasources.jsonl_store import JsonlStore
from sdlc.models.telemetry import LaunchTag, TranscriptTurn, UsageSummary

# Stream of subagent runs, one row per harvest of a subagent transcript
AGENT_RUNS_STREAM = "agent_runs"

# Stream of orchestrator (main-session) model requests
TURNS_STREAM = "turns"

# Stream of pipeline events written by the SDLC tooling
EVENTS_STREAM = "events"

# Stream that maps a session to the item and stage it works on from a moment on
ATTRIBUTIONS_STREAM = "attributions"

# Schema of the in-memory analytics database built from the streams
ANALYTICS_SCHEMA = """
CREATE TABLE agent_runs_raw (
    host TEXT, session_id TEXT, agent_id TEXT, agent_type TEXT, description TEXT,
    item TEXT, block TEXT, task TEXT, role TEXT, models TEXT, efforts TEXT,
    started_at TEXT, ended_at TEXT, duration_seconds REAL, api_calls INTEGER,
    input_tokens INTEGER, output_tokens INTEGER, cache_creation_tokens INTEGER, cache_read_tokens INTEGER,
    total_tokens INTEGER, tool_call_count INTEGER, tool_calls TEXT, harvested_at TEXT
);
CREATE TABLE turns_raw (
    host TEXT, session_id TEXT, message_id TEXT, at TEXT, model TEXT, effort TEXT,
    input_tokens INTEGER, output_tokens INTEGER, cache_creation_tokens INTEGER, cache_read_tokens INTEGER,
    total_tokens INTEGER, tool_call_count INTEGER, tool_calls TEXT
);
CREATE TABLE events (
    at TEXT, host TEXT, event TEXT, item TEXT, task TEXT, status_from TEXT, status_to TEXT,
    value REAL, detail TEXT
);
CREATE TABLE attributions (host TEXT, session_id TEXT, at TEXT, item TEXT, stage TEXT, source TEXT);
CREATE INDEX agent_runs_by_agent ON agent_runs_raw (host, agent_id, harvested_at);
CREATE INDEX turns_by_message ON turns_raw (session_id, message_id);
CREATE INDEX attributions_by_session ON attributions (session_id, at);
CREATE VIEW agent_runs AS
    SELECT * FROM agent_runs_raw AS run
    WHERE rowid = (SELECT rowid FROM agent_runs_raw AS later
                   WHERE later.host = run.host AND later.agent_id = run.agent_id
                   ORDER BY later.harvested_at DESC, later.rowid DESC LIMIT 1);
CREATE VIEW turns AS
    SELECT * FROM turns_raw AS turn
    WHERE rowid = (SELECT MAX(rowid) FROM turns_raw AS same
                   WHERE same.session_id = turn.session_id AND same.message_id = turn.message_id);
CREATE VIEW orchestrator_turns AS
    SELECT turn.*,
        NULLIF((SELECT item FROM attributions AS mark WHERE mark.session_id = turn.session_id AND mark.at <= turn.at
                ORDER BY mark.at DESC LIMIT 1), '') AS item,
        NULLIF((SELECT stage FROM attributions AS mark WHERE mark.session_id = turn.session_id AND mark.at <= turn.at
                ORDER BY mark.at DESC LIMIT 1), '') AS stage
    FROM turns AS turn;
"""


class TelemetryRepository:
    """Records pipeline telemetry in local JSON-lines streams and loads it for analytics."""

    def __init__(self, store: JsonlStore, host: str, now: Callable[[], str] = TimestampHelper.now,
                 blacklist: Optional[List[str]] = None) -> None:
        """Initializes the repository.

        Args:
            store: the local JSON-lines store.
            host: the host name stamped on every record.
            now: the source of record timestamps, replaceable in tests for a deterministic clock.
            blacklist: short ids of items that every report, query, and check leaves out; the streams keep their records.
        """
        self._store = store
        self._host = host
        self._now = now
        self._blacklist = list(blacklist or [])

    @property
    def blacklist(self) -> List[str]:
        """Returns the short ids of the items that analytics leaves out."""
        return list(self._blacklist)

    def record_event(self, event: str, item: Optional[str], task: Optional[str] = None,
                     status_from: Optional[str] = None, status_to: Optional[str] = None,
                     value: Optional[float] = None, detail: Optional[Dict[str, Any]] = None) -> None:
        """Records one pipeline event, such as a status change or a lease wait.

        Args:
            event: the event name, such as `item_status` or `lease_wait`.
            item: the short item id, if any.
            task: the task id, if any.
            status_from: the previous status of a status change.
            status_to: the new status of a status change.
            value: a numeric measure, such as seconds waited.
            detail: extra fields kept as JSON.
        """
        self._store.append(EVENTS_STREAM, {
            "at": self._now(), "host": self._host, "event": event, "item": item, "task": task,
            "status_from": status_from, "status_to": status_to, "value": value, "detail": detail or {},
        })

    def record_attribution(self, session_id: str, item: Optional[str], stage: Optional[str], source: str) -> None:
        """Records that a session works on an item and stage from now on."""
        self._store.append(ATTRIBUTIONS_STREAM, {
            "at": self._now(), "host": self._host, "session_id": session_id,
            "item": item, "stage": stage, "source": source,
        })

    def record_agent_run(self, session_id: str, agent_id: str, agent_type: str, description: str,
                         tag: LaunchTag, summary: UsageSummary) -> None:
        """Records the cumulative usage of one subagent; a later harvest supersedes an earlier one.

        Args:
            session_id: the session that launched the subagent.
            agent_id: the subagent id.
            agent_type: the agent definition name, such as `swe`.
            description: the launch description.
            tag: the SDLC attribution parsed from the description.
            summary: the aggregate usage of the subagent transcript.
        """
        duration = None
        if summary.started_at and summary.ended_at:
            duration = TimestampHelper.seconds_between(summary.started_at, summary.ended_at)
        self._store.append(AGENT_RUNS_STREAM, {
            "host": self._host, "session_id": session_id, "agent_id": agent_id, "agent_type": agent_type,
            "description": description, "item": tag.item, "block": tag.block, "task": tag.task,
            "role": tag.role or agent_type, "models": ",".join(summary.models), "efforts": ",".join(summary.efforts),
            "started_at": TimestampHelper.normalize(summary.started_at or ""),
            "ended_at": TimestampHelper.normalize(summary.ended_at or ""), "duration_seconds": duration,
            "api_calls": summary.api_calls, "input_tokens": summary.usage.input_tokens,
            "output_tokens": summary.usage.output_tokens,
            "cache_creation_tokens": summary.usage.cache_creation_tokens,
            "cache_read_tokens": summary.usage.cache_read_tokens, "total_tokens": summary.usage.total_tokens,
            "tool_call_count": sum(summary.tool_calls.values()), "tool_calls": summary.tool_calls,
            "harvested_at": self._now(),
        })

    def record_turns(self, session_id: str, turns: List[TranscriptTurn]) -> None:
        """Records orchestrator model requests read from a main-session transcript."""
        for turn in turns:
            tool_calls: Dict[str, int] = {}
            for tool_name in turn.tool_names:
                tool_calls[tool_name] = tool_calls.get(tool_name, 0) + 1
            self._store.append(TURNS_STREAM, {
                "host": self._host, "session_id": session_id, "message_id": turn.message_id,
                "at": TimestampHelper.normalize(turn.at), "model": turn.model, "effort": turn.effort,
                "input_tokens": turn.usage.input_tokens, "output_tokens": turn.usage.output_tokens,
                "cache_creation_tokens": turn.usage.cache_creation_tokens,
                "cache_read_tokens": turn.usage.cache_read_tokens, "total_tokens": turn.usage.total_tokens,
                "tool_call_count": len(turn.tool_names), "tool_calls": tool_calls,
            })

    def transcript_offset(self, transcript_key: str) -> int:
        """Returns the byte offset where the previous harvest of a transcript stopped."""
        cursor = self._store.cursor(transcript_key)
        return int(cursor["offset"]) if cursor else 0

    def set_transcript_offset(self, transcript_key: str, offset: int) -> None:
        """Stores the byte offset where the latest harvest of a transcript stopped."""
        self._store.set_cursor(transcript_key, {"offset": offset})

    def load_database(self) -> sqlite3.Connection:
        """Returns an in-memory SQLite database with every stream loaded into its table."""
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.executescript(ANALYTICS_SCHEMA)
        self._load(connection, "agent_runs_raw", AGENT_RUNS_STREAM)
        self._load(connection, "turns_raw", TURNS_STREAM)
        self._load(connection, "events", EVENTS_STREAM)
        self._load(connection, "attributions", ATTRIBUTIONS_STREAM)
        self._exclude_blacklisted(connection)
        return connection

    def _exclude_blacklisted(self, connection: sqlite3.Connection) -> None:
        """Removes every record of a blacklisted item from the analytics database; the streams stay untouched.

        Steps:
            1. Delete the orchestrator turns that the attributions assign to a blacklisted item.
            2. Delete the agent runs, events, and attributions of the blacklisted items.

        The turns go first, because their item comes from the attributions.
        """
        if not self._blacklist:
            return
        marks = ", ".join("?" for _ in self._blacklist)
        connection.execute(
            "DELETE FROM turns_raw WHERE (session_id, message_id) IN "
            f"(SELECT session_id, message_id FROM orchestrator_turns WHERE item IN ({marks}))", self._blacklist)
        for table in ("agent_runs_raw", "events", "attributions"):
            connection.execute(f"DELETE FROM {table} WHERE item IN ({marks})", self._blacklist)

    def _load(self, connection: sqlite3.Connection, table: str, stream: str) -> None:
        """Inserts every record of the stream into the table, keeping only the table's columns."""
        columns = [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
        placeholders = ", ".join("?" for _ in columns)
        rows = []
        for record in self._store.read(stream):
            rows.append([
                json.dumps(record.get(column)) if isinstance(record.get(column), (dict, list)) else record.get(column)
                for column in columns
            ])
        connection.executemany(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", rows)
