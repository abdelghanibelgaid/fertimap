"""Custom exceptions exposed by the public API."""

from __future__ import annotations


class FertimapError(Exception):
    """Base exception for all package-specific errors."""


class ValidationError(FertimapError):
    """Raised when user input fails validation."""


class SiteDataNotFoundError(FertimapError):
    """Raised when Fertimap returns no usable site information."""


class CultureNotFoundError(FertimapError):
    """Raised when a requested crop is not available at a site."""


class UpstreamResponseError(FertimapError):
    """Raised when upstream HTML cannot be parsed as expected."""
