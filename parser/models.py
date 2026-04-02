"""
parser/models.py – Pydantic data models and shared constants.
"""

from typing import Any

from pydantic import BaseModel, field_validator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KNOWN_METRIC_TYPES: set[str] = {"cpu", "memory", "temperature", "disk", "network"}

BYTE_FIELDS: set[str] = {
    "total_bytes",
    "used_bytes",
    "swap_used_bytes",
    "capacity_bytes",
    "free_bytes",
    "provisioned_bytes",
    "rx_bytes_sec",
    "tx_bytes_sec",
}

# Fields whose values are plain text labels (never numeric measurements).
STRING_FIELDS: set[str] = {"datastore_name", "interface"}

# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class RawMetric(BaseModel):
    """One entry from the raw_metrics list – validated on construction."""

    host: str
    metric_type: str
    values: dict[str, Any]
    tags: dict[str, str] = {}

    @field_validator("host")
    @classmethod
    def host_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Leerer Hostname")
        return v

    @field_validator("metric_type")
    @classmethod
    def metric_type_known(cls, v: str) -> str:
        if v not in KNOWN_METRIC_TYPES:
            raise ValueError(f"Unbekannter metric_type: {v!r}")
        return v


class RawInput(BaseModel):
    """Top-level structure of metrics_raw.json."""

    collection_timestamp: str
    source: str
    raw_metrics: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------


class ProcessedMetric(BaseModel):
    """A successfully parsed, normalised, and enriched metric."""

    aduno_id: str
    hostname: str
    type: str
    data: dict[str, Any]
    readable: dict[str, str] = {}
    alerts: list[dict[str, Any]] = []
    tags: dict[str, str] = {}


class ErrorEntry(BaseModel):
    """Records a single parse or validation error."""

    host: str
    metric_type: str
    field: str | None = None
    raw_value: str | None = None
    reason: str


class Alert(BaseModel):
    """A threshold violation alert."""

    aduno_id: str
    type: str
    severity: str
    message: str
    threshold: float | int


class ParseResult(BaseModel):
    """The complete structured output written to output.json."""

    processed_at: str
    source: str
    metrics: list[ProcessedMetric]
    errors: list[ErrorEntry]
    alerts: list[Alert]
    summary: dict[str, Any]
