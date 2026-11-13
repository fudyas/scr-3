import re
from abc import ABC

from sdlc.models.errors import InvalidDescError

# Matches a well-formed slug: uppercase words of letters and digits joined by hyphens
DESC_PATTERN = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)*$")

# Fewest words a DESC slug carries
DESC_MIN_WORDS = 2

# Most words a DESC slug carries
DESC_MAX_WORDS = 8

# Longest DESC slug in characters
DESC_MAX_LENGTH = 64


class DescSlugHelper(ABC):
    """Normalizes and validates the DESC slug of an item id."""

    @staticmethod
    def normalize(text: str) -> str:
        """Returns the text as an uppercase hyphen-joined slug."""
        words = re.split(r"[^A-Za-z0-9]+", text.strip())
        return "-".join(word.upper() for word in words if word)

    @staticmethod
    def validate(desc: str) -> str:
        """Returns the slug when it follows the notation rules.

        Args:
            desc: the candidate DESC slug.

        Returns:
            The same slug.

        Raises:
            InvalidDescError: the slug breaks a notation rule.
        """
        if DESC_PATTERN.match(desc) is None:
            raise InvalidDescError(f"DESC must use uppercase letters, digits, and hyphens: {desc!r}")
        word_count = len(desc.split("-"))
        if not DESC_MIN_WORDS <= word_count <= DESC_MAX_WORDS:
            raise InvalidDescError(f"DESC must have {DESC_MIN_WORDS} to {DESC_MAX_WORDS} words: {desc!r}")
        if len(desc) > DESC_MAX_LENGTH:
            raise InvalidDescError(f"DESC must have at most {DESC_MAX_LENGTH} characters: {desc!r}")
        return desc
