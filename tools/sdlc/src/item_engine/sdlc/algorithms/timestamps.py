from abc import ABC
from datetime import datetime, timezone


class TimestampHelper(ABC):
    """Produces and normalizes UTC timestamps so ledger, telemetry, and transcripts sort together."""

    @staticmethod
    def now() -> str:
        """Returns the current UTC time as `YYYY-MM-DDTHH:MM:SS.mmmZ`."""
        return TimestampHelper.format(datetime.now(timezone.utc))

    @staticmethod
    def format(moment: datetime) -> str:
        """Returns the moment in UTC as `YYYY-MM-DDTHH:MM:SS.mmmZ`."""
        return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"

    @staticmethod
    def seconds_between(start: str, end: str) -> float:
        """Returns the seconds from the start timestamp to the end timestamp."""
        start_moment = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_moment = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return (end_moment - start_moment).total_seconds()

    @staticmethod
    def normalize(text: str) -> str:
        """Returns an ISO timestamp in the normalized UTC form; unparsable text is returned unchanged."""
        if not text:
            return text
        try:
            return TimestampHelper.format(datetime.fromisoformat(text.replace("Z", "+00:00")))
        except ValueError:
            return text
