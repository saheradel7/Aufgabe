"""I/O helpers and the main metric-processing pipeline."""

import json
import logging
from pathlib import Path

from .alerts import check_thresholds
from .models import ErrorEntry, ParseResult, ProcessedMetric, RawInput, RawMetric
from .utils import convert_values, resolve_aduno_id

log = logging.getLogger(__name__)


def load_raw_input(path: Path) -> RawInput:
    """Read and validate metrics_raw.json."""
    log.info("Reading input: %s", path)
    with path.open(encoding="utf-8") as fh:
        return RawInput.model_validate(json.load(fh))


def load_host_mapping(path: Path) -> dict[str, str]:
    """Read the host → aduno_id mapping from host_mapping.json."""
    log.info("Reading mapping: %s", path)
    with path.open(encoding="utf-8") as fh:
        return json.load(fh).get("host_mapping", {})


def _validation_reason(exc: Exception) -> str:
    """Extract a readable message from a Pydantic ValidationError (or any exception)."""
    try:
        return str(exc.errors()[0]["msg"])  # type: ignore[attr-defined]
    except Exception:
        return str(exc)


def process_metrics(raw_input: RawInput, host_mapping: dict[str, str]) -> ParseResult:
    """
    Validate → convert → enrich → alert-check every raw metric entry.
    Invalid entries are never silently dropped; errors are collected instead.
    """
    metrics: list[ProcessedMetric] = []
    errors:  list[ErrorEntry]      = []
    all_alerts                     = []
    hosts_seen: set[str]           = set()

    for entry in raw_input.raw_metrics:
        # Validate structure with Pydantic
        try:
            raw = RawMetric.model_validate(entry)
        except Exception as exc:
            host  = entry.get("host", "")
            mtype = entry.get("metric_type", "unknown")
            errors.append(ErrorEntry(host=host, metric_type=mtype, reason=_validation_reason(exc)))
            log.warning("Skipping invalid entry host=%r: %s", host, errors[-1].reason)
            continue

        # Convert string values and resolve host identity
        clean_data, readable = convert_values(raw.values, raw.host, raw.metric_type, errors)
        aduno_id = resolve_aduno_id(raw.host, host_mapping)
        hosts_seen.add(raw.host)

        # Build the processed metric and check thresholds
        metric = ProcessedMetric(
            aduno_id=aduno_id, hostname=raw.host, type=raw.metric_type,
            data=clean_data, readable=readable, tags=raw.tags,
        )
        metric_alerts      = check_thresholds(metric)
        metric.alerts      = [a.model_dump() for a in metric_alerts]
        all_alerts.extend(metric_alerts)

        metrics.append(metric)
        log.info("OK  %-40s  %-12s  →  %s", raw.host, raw.metric_type, aduno_id)

    return ParseResult(
        processed_at=raw_input.collection_timestamp,
        source=raw_input.source,
        metrics=metrics,
        errors=errors,
        alerts=all_alerts,
        summary={
            "total_raw": len(raw_input.raw_metrics),
            "processed_ok": len(metrics),
            "errors": len(errors),
            "alerts_generated": len(all_alerts),
            "hosts_seen": len(hosts_seen),
        },
    )
