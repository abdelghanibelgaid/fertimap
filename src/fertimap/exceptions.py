"""Custom exceptions exposed by the public API."""

from __future__ import annotations


class FertiMapError(Exception):
    """Base exception for all package-specific errors."""


class ValidationError(FertiMapError):
    """Raised when user input fails validation."""


class SiteDataNotFoundError(FertiMapError):
    """Raised when Fertimap returns no usable site information."""


class CultureNotFoundError(FertiMapError):
    """Raised when a requested crop is not available at a site."""


class UpstreamResponseError(FertiMapError):
    """Raised when upstream HTML cannot be parsed as expected."""
