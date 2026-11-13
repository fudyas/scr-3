from typing import Any, Mapping, Self

from pydantic import BaseModel, ConfigDict
from pydantic_core import to_json


class StrictModel(BaseModel):
    """Base of every pydantic model: rejects unknown fields, validates strict types, and stays mutable."""

    model_config = ConfigDict(strict=True, extra="forbid")

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> Self:
        """Builds the model from a parsed document or a database row, validated in JSON mode.

        JSON mode accepts enum values and UUID, path, and timestamp strings. The conversion through
        `to_json` turns driver values such as `UUID`, `datetime`, `Path`, and enum members into JSON. A
        mapping that is no dict, such as a database row mapping, is accepted.
        Strict mode still rejects coercion and unknown fields, including unknown nested keys.

        Args:
            document: the parsed YAML or JSON document, environment values, or database row.

        Returns:
            The validated model.

        Raises:
            ValidationError: the document breaks the model.
        """

        # Copies a mapping that is no dict, such as a database row mapping, because `to_json` serializes only dicts
        return cls.model_validate_json(to_json(dict(document)))
