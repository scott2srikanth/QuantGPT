"""Integration Layer exceptions.

These are backend-neutral. Adapters translate backend-specific errors into
these so callers never depend on the underlying broker/trading platform.
"""

from __future__ import annotations


class IntegrationError(Exception):
    """Base error for all Integration Layer failures."""


class BackendUnreachableError(IntegrationError):
    """Backend could not be reached (network, DNS, connection refused)."""


class BackendAuthError(IntegrationError):
    """Authentication with the backend failed (bad key, expired token)."""


class BackendRateLimitError(IntegrationError):
    """Backend rate-limited the request."""


class BackendValidationError(IntegrationError):
    """Backend rejected the request due to invalid parameters."""

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class BackendNotFoundError(IntegrationError):
    """Requested resource was not found in the backend."""


class BackendServerError(IntegrationError):
    """Backend returned an internal server error (5xx)."""


class BackendTimeoutError(IntegrationError):
    """Request to the backend timed out."""


class AdapterNotImplementedError(IntegrationError):
    """A capability is not implemented by the active backend adapter."""
