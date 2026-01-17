"""Custom exceptions for elogfetch."""

from __future__ import annotations


class FetchElogError(Exception):
    """Base exception for elogfetch."""

    pass


class AuthenticationError(FetchElogError):
    """Kerberos authentication failed."""

    pass


class APIError(FetchElogError):
    """API request failed."""

    def __init__(
        self, message: str, status_code: int | None = None, response: str | None = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class DatabaseError(FetchElogError):
    """Database operation failed."""

    pass


class LockError(FetchElogError):
    """Failed to acquire lock."""

    pass
