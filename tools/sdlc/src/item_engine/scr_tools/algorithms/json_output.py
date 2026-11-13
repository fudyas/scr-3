import json
from abc import ABC
from typing import Any

from pydantic_core import to_jsonable_python


class JsonOutputHelper(ABC):
    """Renders the JSON output of the tool command-line interfaces in one shared layout."""

    @staticmethod
    def render(value: Any) -> str:
        """Returns the value as JSON with a two-space indent and UTF-8 characters without escapes.

        Models render by field alias at any depth of lists and dictionaries; enums, paths, and dates render as
        their JSON values.

        Args:
            value: a model, a list or dictionary that holds models, or plain JSON data.

        Returns:
            The JSON text without a trailing newline.
        """
        return json.dumps(to_jsonable_python(value, by_alias=True), indent=2, ensure_ascii=False)
