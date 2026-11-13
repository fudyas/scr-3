from pathlib import Path
from typing import Optional

from sdlc.algorithms.launch_tag import LaunchTagParser
from sdlc.algorithms.mark_parser import END_STAGE, MarkParser
from sdlc.algorithms.transcript_usage import TranscriptUsageHelper
from sdlc.datasources.transcript_source import TranscriptSource
from sdlc.models.telemetry import HarvestReport
from sdlc.repositories.telemetry_repository import TelemetryRepository


class TelemetryUsecases:
    """Harvests token usage from Claude Code transcripts and attributes it to SDLC items."""

    def __init__(self, telemetry: TelemetryRepository, transcripts: TranscriptSource, prefix: str) -> None:
        """Initializes the usecases.

        Args:
            telemetry: the telemetry repository.
            transcripts: the transcript data source.
            prefix: the item id prefix, such as `ITM`.
        """
        self._telemetry = telemetry
        self._transcripts = transcripts
        self._prefix = prefix

    def on_bash_command(self, session_id: str, command: str, output: Optional[str] = None) -> bool:
        """Records an attribution when the call ran an SDLC `mark`.

        Args:
            session_id: the session that ran the command.
            command: the Bash command line.
            output: the standard output of the command, where `mark` prints its result line, or None when
                the hook payload has no tool response.

        Returns:
            True when the call ran a mark and an attribution was recorded.
        """
        mark = MarkParser.find(command, output, self._prefix)
        if mark is None:
            return False
        if mark.stage == END_STAGE:
            self._telemetry.record_attribution(session_id, "", "", "mark")
        else:
            self._telemetry.record_attribution(session_id, mark.item, mark.stage, "mark")
        return True

    def on_session_stop(self, session_id: str, transcript_path: Path) -> int:
        """Records the orchestrator turns written since the previous harvest of the session.

        Returns:
            The number of turns recorded.
        """
        key = f"session-{session_id}"
        chunk = self._transcripts.read_from(transcript_path, self._telemetry.transcript_offset(key))
        turns = TranscriptUsageHelper.turns(chunk.lines, include_sidechain=False)
        self._telemetry.record_turns(session_id, turns)
        self._telemetry.set_transcript_offset(key, chunk.next_offset)
        return len(turns)

    def on_subagent_stop(self, session_id: str, agent_id: str, agent_type: Optional[str],
                         transcript_path: Path) -> None:
        """Records the cumulative usage of a subagent from its own transcript, when the transcript exists.

        Args:
            session_id: the session that launched the subagent.
            agent_id: the subagent id.
            agent_type: the agent type from the hook, if given.
            transcript_path: the subagent transcript.
        """

        # Skips hook-only stops, such as an evaluator run, that leave no transcript to harvest
        if not self._transcripts.exists(transcript_path):
            return
        meta = self._transcripts.subagent_meta(transcript_path)
        description = str(meta.get("description") or "")
        resolved_type = agent_type or str(meta.get("agentType") or "unknown")
        turns = TranscriptUsageHelper.turns(self._transcripts.read_all(transcript_path), include_sidechain=True)
        self._telemetry.record_agent_run(
            session_id, agent_id, resolved_type, description,
            LaunchTagParser.parse(description, self._prefix), TranscriptUsageHelper.summarize(turns),
        )

    def backfill(self, project_dir: Path) -> HarvestReport:
        """Harvests every transcript of the project that earlier hooks missed.

        Args:
            project_dir: the project directory whose Claude Code transcripts are read.

        Returns:
            Counts of the sessions, turns, and agent runs recorded.
        """
        sessions = turns = agent_runs = 0
        project_dir_name = TranscriptSource.project_dir_name(project_dir)
        for session_transcript in self._transcripts.session_transcripts(project_dir_name):
            session_id = session_transcript.stem
            sessions += 1
            turns += self.on_session_stop(session_id, session_transcript)
            for agent_transcript in self._transcripts.subagent_transcripts(session_transcript):
                agent_id = agent_transcript.stem.removeprefix("agent-")
                self.on_subagent_stop(session_id, agent_id, None, agent_transcript)
                agent_runs += 1
        return HarvestReport(sessions=sessions, turns=turns, agent_runs=agent_runs)
