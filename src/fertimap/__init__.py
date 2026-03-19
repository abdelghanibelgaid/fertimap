"""Public package interface for FertiMap Library."""

from fertimap.client import FertimapClient
from fertimap.exceptions import (
    CropNotFoundError,
    FertimapError,
    SiteDataNotFoundError,
    UpstreamResponseError,
    ValidationError,
)
from fertimap.utils import apply_column_map, ensure_dataframe

__all__ = [
    "CropNotFoundError",
    "FertimapClient",
    "FertimapError",
    "SiteDataNotFoundError",
    "UpstreamResponseError",
    "ValidationError",
    "apply_column_map",
    "ensure_dataframe",
]

__version__ = "0.5.0"
