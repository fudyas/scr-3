from typing import Dict, List, Optional

from pydantic import Field

from primitives.models.strict_model import StrictModel


class TokenUsage(StrictModel):
    """Token counts by class for one or more model requests."""

    # Counts the input tokens
    input_tokens: int = 0

    # Counts the output tokens
    output_tokens: int = 0

    # Counts the tokens written to the prompt cache
    cache_creation_tokens: int = 0

    # Counts the tokens read from the prompt cache
    cache_read_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Returns the sum of every token class."""
        return self.input_tokens + self.output_tokens + self.cache_creation_tokens + self.cache_read_tokens


class TranscriptTurn(StrictModel):
    """One deduplicated model request from a transcript."""

    # Identifies the model message
    message_id: str

    # Gives the time of the request
    at: str

    # Names the model that served the request
    model: Optional[str] = None

    # Gives the reasoning effort of the request
    effort: Optional[str] = None
    usage: TokenUsage = Field(default_factory=TokenUsage, description="Counts the tokens of the request.")
    tool_names: List[str] = Field(default_factory=list, description="Lists the tools that the request called.")


class UsageSummary(StrictModel):
    """The aggregate of every request in one transcript."""

    # Gives the time of the first request
    started_at: Optional[str] = None

    # Gives the time of the last request
    ended_at: Optional[str] = None

    # Counts the requests
    api_calls: int = 0
    models: List[str] = Field(default_factory=list, description="Lists the models that served the requests.")
    efforts: List[str] = Field(default_factory=list, description="Lists the reasoning efforts of the requests.")
    usage: TokenUsage = Field(default_factory=TokenUsage, description="Sums the tokens of every request.")
    tool_calls: Dict[str, int] = Field(
        default_factory=dict, description="Counts the calls of each tool, keyed by tool name."
    )


class LaunchTag(StrictModel):
    """The SDLC attribution parsed from a subagent launch description."""

    # Identifies the item named in the launch description
    item: Optional[str] = None

    # Identifies the block named in the launch description
    block: Optional[str] = None

    # Identifies the task named in the launch description
    task: Optional[str] = None

    # Names the pipeline role named in the launch description
    role: Optional[str] = None

    # Holds the free-text summary of the launch
    summary: str = ""


class HarvestReport(StrictModel):
    """What one harvest pass recorded."""

    # Counts the sessions that were recorded
    sessions: int = 0

    # Counts the model requests that were recorded
    turns: int = 0

    # Counts the subagent runs that were recorded
    agent_runs: int = 0
