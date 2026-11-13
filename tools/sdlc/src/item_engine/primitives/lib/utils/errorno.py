from __future__ import annotations

from enum import Enum


class ErrorNo(Enum):
    """Error identities, numeric codes, and default reasons."""

    ESUCCESS = (0, "success")
    EFORMAT = (10, "invalid format")
    EBADARG = (11, "bad arguments")
    ENOTFOUND = (20, "resource not found")
    EEXISTS = (21, "resource already exists")
    EBADSTATE = (22, "invalid state")
    ENOTREADY = (23, "not ready")
    ENOENT = (24, "no such path")
    EFAILED = (30, "operation failed")
    ENOTSUP = (31, "operation not supported")
    EDENIED = (32, "access denied")
    EIGNORED = (33, "request ignored")
    EBADIO = (34, "I/O operation failed")
    EAGAIN = (35, "try again later")
    EABORTED = (36, "operation aborted")
    ECONFIG = (37, "configuration or deployment fault")
    EUNKNOWN = (99, "unknown error")

    def __init__(self, code: int, reason: str) -> None:
        """Initializes the error code and reason string."""
        self.code: int = code
        self.reason: str = reason

    @classmethod
    def from_code(cls, code: int) -> ErrorNo:
        """Returns the matching ErrorNo member for the code, or EUNKNOWN if none matches."""
        for member in cls:
            if member.code == code:
                return member
        return cls.EUNKNOWN
