import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from sdlc.algorithms.timestamps import TimestampHelper
from sdlc.wiring import AppWiring

# File in the telemetry directory that collects hook failures for `stats doctor` follow-up
HOOK_ERRORS_FILE = "hook-errors.log"


class TelemetryHookController:
    """Adapts Claude Code hook payloads into telemetry harvest calls; never fails the session."""

    def __init__(self, wiring: AppWiring) -> None:
        """Initializes the controller.

        Args:
            wiring: the application wiring.
        """
        self._wiring = wiring

    def handle(self, payload: Dict[str, Any]) -> None:
        """Routes one hook payload to the matching telemetry usecase.

        Args:
            payload: the JSON object Claude Code writes to the hook's standard input.
        """
        usecases = self._wiring.telemetry_usecases
        event = payload.get("hook_event_name", "")
        session_id = str(payload.get("session_id") or "unknown")
        if event == "PostToolUse" and payload.get("tool_name") == "Bash":
            usecases.on_bash_command(session_id, str((payload.get("tool_input") or {}).get("command") or ""),
                                     self._tool_output(payload))
        elif event == "SubagentStop" and payload.get("agent_transcript_path"):
            usecases.on_subagent_stop(session_id, str(payload.get("agent_id") or "unknown"),
                                      payload.get("agent_type"), Path(payload["agent_transcript_path"]))
        elif event in ("Stop", "SessionEnd") and payload.get("transcript_path"):
            usecases.on_session_stop(session_id, Path(payload["transcript_path"]))

    @staticmethod
    def _tool_output(payload: Dict[str, Any]) -> Optional[str]:
        """Returns the standard output of the Bash call, or None when the payload carries no tool response."""
        response = payload.get("tool_response")
        if isinstance(response, dict):
            return str(response.get("stdout") or "")
        return response if isinstance(response, str) else None


class TelemetryHookEntry:
    """Process entry point of the telemetry hook."""

    @staticmethod
    def main() -> int:
        """Handles the hook payload on standard input and always returns 0."""
        try:
            start_dir = Path(os.environ.get("SDLC_PROJECT_DIR") or Path.cwd())
            wiring = AppWiring.from_directory(start_dir)
        except Exception:
            return 0
        try:
            TelemetryHookController(wiring).handle(json.loads(sys.stdin.read() or "{}"))
        except Exception:
            # Keeps the failure for diagnosis instead of interrupting the session
            log_path = wiring.settings.telemetry_dir / HOOK_ERRORS_FILE
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(f"{TimestampHelper.now()} {traceback.format_exc()}\n")
        return 0


if __name__ == "__main__":
    sys.exit(TelemetryHookEntry.main())
