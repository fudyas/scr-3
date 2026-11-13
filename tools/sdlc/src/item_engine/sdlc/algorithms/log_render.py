from abc import ABC

from sdlc.models.run_log import LogEntry, LogLevel

# ANSI escape that resets all attributes
RESET = "\033[0m"

# SGR code per role, matching each agent's declared color: run bold cyan (the run spine),
# planner blue, swe green, validator orange, integrator yellow, qa red
ROLE_CODES = {
    "run": "1;36",
    "planner": "34",
    "swe": "32",
    "validator": "38;5;208",
    "integrator": "33",
    "qa": "31",
}

# SGR code that overrides the role color by severity: warn bold yellow, error bold red
LEVEL_CODES = {
    LogLevel.WARN: "1;33",
    LogLevel.ERROR: "1;31",
}

# Column width of the role field, sized to the longest role (`integrator`)
ROLE_WIDTH = 10

# Column width of the task or block tag field, such as `TSK-0001`
TAG_WIDTH = 8


class LogRenderHelper(ABC):
    """Renders a run-log entry as one line, colored for a terminal."""

    @staticmethod
    def render(entry: LogEntry, use_color: bool) -> str:
        """Returns the one-line rendering of an entry.

        Args:
            entry: the run-log line to render.
            use_color: whether to wrap the line in ANSI color codes.

        Returns:
            `HH:MM:SS  <role>  <tag>  <message>`, colored by role, or bold by severity.
        """
        tag = entry.task or entry.block or ""
        line = (f"{LogRenderHelper._clock(entry.at)}  {entry.role:<{ROLE_WIDTH}}  "
                f"{tag:<{TAG_WIDTH}}  {entry.message}")
        if not use_color:
            return line
        code = LEVEL_CODES.get(entry.level) or ROLE_CODES.get(entry.role)
        return f"\033[{code}m{line}{RESET}" if code else line

    @staticmethod
    def _clock(timestamp: str) -> str:
        """Returns the `HH:MM:SS` part of an ISO timestamp, or the raw text when it is too short."""
        return timestamp[11:19] if len(timestamp) >= 19 and timestamp[10:11] == "T" else timestamp
