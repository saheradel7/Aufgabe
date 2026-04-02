"""Utility helpers: unit conversion, ID resolution, value normalisation."""

import hashlib
import logging
from typing import Any

from .models import BYTE_FIELDS, STRING_FIELDS, ErrorEntry

log = logging.getLogger(__name__)


def bytes_to_human(num_bytes: int | float) -> str:
    """Convert a byte count to a human-readable string, e.g. '128.0 GB'."""
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} EB"


def resolve_aduno_id(hostname: str, mapping: dict[str, str]) -> str:
    """Return the mapped aduno_id, or generate one from the hostname's SHA-256."""
    if hostname in mapping:
        return mapping[hostname]
    sha = hashlib.sha256(hostname.encode()).hexdigest()[:8]
    return f"ADN-HOST-UNKNOWN-{sha}"


def _to_number(raw: str) -> int | float | None:
    """Parse a string as int or float. Returns None if the string is not numeric."""
    try:
        return int(raw)
    except ValueError:
        try:
            return float(raw)
        except ValueError:
            return None


def convert_values(
    values: dict[str, Any],
    host: str,
    metric_type: str,
    errors: list[ErrorEntry],
) -> tuple[dict[str, Any], dict[str, str]]:
    """
    Convert each value string to int/float where possible.

    Non-numeric strings are recorded in *errors* and the field is skipped.
    Known text-label fields (e.g. datastore_name) pass through unchanged.
    Byte fields also get a human-readable entry in the returned readable dict.
    """
    clean: dict[str, Any] = {}
    readable: dict[str, str] = {}

    for key, raw in values.items():
        # Non-string or known text-label → keep as-is
        if not isinstance(raw, str) or key in STRING_FIELDS:
            clean[key] = raw
            continue

        value = _to_number(raw)

        if value is None:
            errors.append(ErrorEntry(
                host=host, metric_type=metric_type,
                field=key, raw_value=raw, reason="Nicht-numerischer Wert",
            ))
            log.warning("Non-numeric value %s.%s=%r – field skipped", host, key, raw)
            continue

        clean[key] = value
        if key in BYTE_FIELDS:
            readable[key] = bytes_to_human(value)

    return clean, readable
