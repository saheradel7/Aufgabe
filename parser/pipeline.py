"""
parser/pipeline.py – I/O and the main processing pipeline.
"""

import json
import logging
from pathlib import Path

from .alerts import check_thresholds
from .models import ErrorEntry, ParseResult, ProcessedMetric, RawInput, RawMetric
from .utils import convert_values, resolve_aduno_id

log = logging.getLogger(__name__)


def load_raw_input(path: Path) -> RawInput:
    """Load and validate the top-level metrics_raw.json file."""
    log.info("Reading input: %s", path)
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return RawInput.model_validate(data)


def load_host_mapping(path: Path) -> dict[str, str]:
    """Load the host → aduno_id mapping from host_mapping.json."""
    log.info("Reading mapping: %s", path)
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("host_mapping", {})


def process_metrics(
    raw_input: RawInput,
    host_mapping: dict[str, str],
) -> ParseResult:
    """
    Run the full parse pipeline for all raw metrics.

    Steps per entry:
      1. Structural validation (Pydantic)
      2. Value type conversion + normalisation
      3. aduno_id enrichment
      4. Threshold / alerting checks

    Invalid entries are never silently dropped – errors are collected and
    included in the returned :class:`ParseResult`.
    """
    metrics: list[ProcessedMetric] = []
    errors: list[ErrorEntry] = []
    all_alerts = []
    hosts_seen: set[str] = set()

    for entry in raw_input.raw_metrics:
        # 1. Validate structure
        try:
            raw = RawMetric.model_validate(entry)
        except Exception as exc:
            host = entry.get("host", "")
            mtype = entry.get("metric_type", "unknown")
            reason = str(exc.errors()[0]["msg"]) if hasattr(exc, "errors") else str(exc)
            errors.append(ErrorEntry(host=host, metric_type=mtype, reason=reason))
            log.warning("Skipping invalid entry host=%r: %s", host, reason)
            continue

        # 2. Convert values
        clean_data, readable = convert_values(raw.values, raw.host, raw.metric_type, errors)

        # 3. Enrich with aduno_id
        aduno_id = resolve_aduno_id(raw.host, host_mapping)
        hosts_seen.add(raw.host)

        # 4. Build metric object
        metric = ProcessedMetric(
            aduno_id=aduno_id,
            hostname=raw.host,
            type=raw.metric_type,
            data=clean_data,
            readable=readable,
            tags=raw.tags,
        )

        # 5. Check thresholds
        metric_alerts = check_thresholds(metric)
        metric.alerts = [a.model_dump() for a in metric_alerts]
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
