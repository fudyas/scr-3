import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from sdlc.models.errors import SdlcError
from sdlc.models.stats import StatsTable
from sdlc.repositories.telemetry_repository import TelemetryRepository

# Per-item totals: orchestrator and subagent tokens, runs, tasks, and reworks
ITEMS_REPORT = """
WITH agent AS (
    SELECT item, SUM(total_tokens) AS tokens, SUM(output_tokens) AS output, COUNT(*) AS runs,
           COUNT(DISTINCT task) AS tasks, ROUND(SUM(duration_seconds)) AS agent_seconds
    FROM agent_runs WHERE item IS NOT NULL GROUP BY item),
orchestrator AS (
    SELECT item, SUM(total_tokens) AS tokens, COUNT(*) AS calls
    FROM orchestrator_turns WHERE item IS NOT NULL GROUP BY item),
rework AS (SELECT item, COUNT(*) AS reworks FROM events WHERE event = 'task_rework' GROUP BY item),
ids AS (SELECT item FROM agent UNION SELECT item FROM orchestrator)
SELECT ids.item, COALESCE(orchestrator.tokens, 0) AS orchestrator_tokens, COALESCE(agent.tokens, 0) AS agent_tokens,
       COALESCE(orchestrator.tokens, 0) + COALESCE(agent.tokens, 0) AS total_tokens,
       COALESCE(agent.output, 0) AS agent_output_tokens, COALESCE(agent.runs, 0) AS agent_runs,
       COALESCE(agent.tasks, 0) AS tasks, COALESCE(rework.reworks, 0) AS reworks, agent.agent_seconds
FROM ids LEFT JOIN agent USING (item) LEFT JOIN orchestrator USING (item) LEFT JOIN rework USING (item)
WHERE (:item IS NULL OR ids.item = :item)
ORDER BY ids.item
"""

# Per-role averages: tokens per run and per task, duration, tool calls, models
ROLES_REPORT = """
SELECT role, COUNT(*) AS runs, ROUND(AVG(total_tokens)) AS avg_tokens_per_run,
       ROUND(1.0 * SUM(total_tokens) / NULLIF(COUNT(DISTINCT CASE WHEN task IS NOT NULL THEN item || task END), 0))
           AS avg_tokens_per_task,
       ROUND(AVG(output_tokens)) AS avg_output_tokens,
       ROUND(100.0 * SUM(cache_read_tokens) / NULLIF(SUM(total_tokens), 0), 1) AS cache_read_percent,
       ROUND(AVG(duration_seconds)) AS avg_seconds, ROUND(AVG(tool_call_count), 1) AS avg_tool_calls,
       GROUP_CONCAT(DISTINCT models) AS models, GROUP_CONCAT(DISTINCT efforts) AS efforts
FROM agent_runs WHERE (:item IS NULL OR item = :item)
GROUP BY role ORDER BY SUM(total_tokens) DESC
"""

# Orchestrator tokens by item and stage
STAGES_REPORT = """
SELECT COALESCE(item, '-') AS item, COALESCE(stage, '-') AS stage, COUNT(*) AS calls,
       SUM(total_tokens) AS tokens, SUM(output_tokens) AS output_tokens, GROUP_CONCAT(DISTINCT model) AS models
FROM orchestrator_turns WHERE (:item IS NULL OR item = :item)
GROUP BY item, stage ORDER BY item, stage
"""

# Per-task cost: engineer runs and tokens, every role's tokens, and reworks
TASKS_REPORT = """
WITH rework AS (
    SELECT item, task, COUNT(*) AS reworks,
           GROUP_CONCAT(json_extract(detail, '$.stage')) AS rework_stages
    FROM events WHERE event = 'task_rework' GROUP BY item, task)
SELECT run.item, run.task,
       SUM(CASE WHEN run.role = 'swe' THEN 1 ELSE 0 END) AS swe_runs,
       SUM(CASE WHEN run.role = 'swe' THEN run.total_tokens ELSE 0 END) AS swe_tokens,
       SUM(run.total_tokens) AS all_role_tokens, COALESCE(rework.reworks, 0) AS reworks, rework.rework_stages
FROM agent_runs AS run LEFT JOIN rework ON rework.item = run.item AND rework.task = run.task
WHERE run.task IS NOT NULL AND (:item IS NULL OR run.item = :item)
GROUP BY run.item, run.task ORDER BY run.item, run.task
"""

# Latest subagent runs with their attribution and usage
AGENTS_REPORT = """
SELECT started_at, item, COALESCE(task, block) AS scope, role, agent_type, models, efforts, total_tokens,
       output_tokens, ROUND(duration_seconds) AS seconds, tool_call_count AS tools, description
FROM agent_runs WHERE (:item IS NULL OR item = :item)
ORDER BY started_at DESC LIMIT 50
"""

# Lease waits and holds per lease
LEASES_REPORT = """
SELECT json_extract(detail, '$.lease') AS lease, event, COUNT(*) AS count, ROUND(AVG(value), 1) AS avg_seconds,
       ROUND(MAX(value), 1) AS max_seconds
FROM events WHERE event IN ('lease_acquired', 'lease_released') AND (:item IS NULL OR item = :item)
GROUP BY lease, event ORDER BY lease, event
"""

# Per-item summary: orchestrator row, one row per agent role, and a total row that always exists
ITEM_SUMMARY_REPORT = """
WITH orchestrator AS (
    SELECT COUNT(*) AS runs, COALESCE(SUM(total_tokens), 0) AS tokens, COALESCE(SUM(output_tokens), 0) AS output_tokens
    FROM orchestrator_turns WHERE item = :item),
agent AS (
    SELECT role, COUNT(*) AS runs, SUM(total_tokens) AS tokens, SUM(output_tokens) AS output_tokens,
           ROUND(SUM(duration_seconds)) AS seconds, COUNT(DISTINCT task) AS tasks
    FROM agent_runs WHERE item = :item GROUP BY role),
agent_total AS (
    SELECT COUNT(*) AS runs, COALESCE(SUM(total_tokens), 0) AS tokens, COALESCE(SUM(output_tokens), 0) AS output_tokens,
           COALESCE(ROUND(SUM(duration_seconds)), 0) AS seconds, COUNT(DISTINCT task) AS tasks
    FROM agent_runs WHERE item = :item),
summary AS (
    SELECT 0 AS position, 'orchestrator' AS role, runs, tokens, output_tokens, NULL AS seconds, NULL AS tasks,
           NULL AS reworks
    FROM orchestrator WHERE runs > 0
    UNION ALL
    SELECT 1, role, runs, tokens, output_tokens, seconds, tasks, NULL FROM agent
    UNION ALL
    SELECT 2, 'total', orchestrator.runs + agent_total.runs, orchestrator.tokens + agent_total.tokens,
           orchestrator.output_tokens + agent_total.output_tokens, agent_total.seconds, agent_total.tasks,
           (SELECT COUNT(*) FROM events WHERE event = 'task_rework' AND item = :item)
    FROM orchestrator, agent_total)
SELECT role, runs, tokens, output_tokens, seconds, tasks, reworks FROM summary ORDER BY position, tokens DESC
"""

# Every canned report by name
REPORTS: Dict[str, str] = {
    "items": ITEMS_REPORT,
    "roles": ROLES_REPORT,
    "stages": STAGES_REPORT,
    "tasks": TASKS_REPORT,
    "agents": AGENTS_REPORT,
    "leases": LEASES_REPORT,
}

# Every name the `stats` command accepts as its report: the canned reports and the special ones
STATS_COMMAND_REPORTS: Tuple[str, ...] = (*REPORTS, "sql", "doctor", "harvest")


class StatsUsecases:
    """Answers analytics questions over the local pipeline telemetry."""

    def __init__(self, telemetry: TelemetryRepository) -> None:
        """Initializes the usecases.

        Args:
            telemetry: the telemetry repository.
        """
        self._telemetry = telemetry

    def report(self, name: str, item: Optional[str]) -> StatsTable:
        """Returns a canned report, optionally limited to one item.

        Raises:
            SdlcError: the report name is unknown.
        """
        if name not in REPORTS:
            raise SdlcError(f"unknown report {name!r} (known: {', '.join(REPORTS)})")
        return self._run(REPORTS[name], {"item": item})

    def item_summary(self, item: str) -> StatsTable:
        """Returns the per-role token summary of one item, ending in a total row."""
        return self._run(ITEM_SUMMARY_REPORT, {"item": item})

    def query(self, sql: str) -> StatsTable:
        """Returns the result of an ad-hoc read-only SQL query over the telemetry tables.

        Raises:
            SdlcError: the query fails.
        """
        return self._run(sql, {})

    def doctor(self) -> StatsTable:
        """Returns stream sizes and attribution coverage, the signals of a broken capture."""
        checks = [
            ("agent runs", "SELECT COUNT(*) FROM agent_runs"),
            ("agent runs without an item tag", "SELECT COUNT(*) FROM agent_runs WHERE item IS NULL"),
            ("agent runs with zero tokens", "SELECT COUNT(*) FROM agent_runs WHERE total_tokens = 0 AND api_calls > 0"),
            ("agent runs without a transcript", "SELECT COUNT(*) FROM agent_runs WHERE total_tokens = 0 AND api_calls = 0"),
            ("orchestrator turns", "SELECT COUNT(*) FROM turns"),
            ("orchestrator turns attributed", "SELECT COUNT(*) FROM orchestrator_turns WHERE item IS NOT NULL"),
            ("pipeline events", "SELECT COUNT(*) FROM events"),
            ("attributions", "SELECT COUNT(*) FROM attributions"),
            ("latest agent harvest", "SELECT MAX(harvested_at) FROM agent_runs_raw"),
            ("latest orchestrator turn", "SELECT MAX(at) FROM turns"),
        ]
        connection = self._telemetry.load_database()
        rows = [[label, connection.execute(sql).fetchone()[0]] for label, sql in checks]
        rows.append(["items left out by the blacklist", ", ".join(self._telemetry.blacklist) or "-"])
        return StatsTable(columns=["check", "value"], rows=rows)

    def _run(self, sql: str, parameters: Dict[str, Any]) -> StatsTable:
        """Returns the rows of a query run against a fresh in-memory telemetry database.

        Raises:
            SdlcError: the query fails.
        """
        connection = self._telemetry.load_database()
        try:
            cursor = connection.execute(sql, parameters)
        except sqlite3.Error as error:
            raise SdlcError(f"query failed: {error}") from error
        columns = [column[0] for column in cursor.description or []]
        return StatsTable(columns=columns, rows=[list(row) for row in cursor.fetchall()])
