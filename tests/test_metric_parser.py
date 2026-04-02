"""
tests/test_metric_parser.py – Unit tests for the aduno® Metric Parser.
Run with:  pytest tests/ -v
"""

from parser.models import ErrorEntry, ProcessedMetric, RawInput
from parser.alerts import check_thresholds
from parser.utils import convert_values
from parser.pipeline import process_metrics

MAPPING = {"esx-prod-01.customer-a.local": "ADN-HOST-0001"}


def _make_raw_input(raw_metrics: list) -> RawInput:
    return RawInput(
        collection_timestamp="2025-04-02T10:15:00Z",
        source="test",
        raw_metrics=raw_metrics,
    )


def test_pipeline_valid_entry():
    """Happy path: valid metric is processed and enriched with the correct aduno_id."""
    result = process_metrics(
        _make_raw_input([
            {"host": "esx-prod-01.customer-a.local", "metric_type": "cpu",
             "values": {"usage_percent": "78.5", "cores": "16"}, "tags": {}},
        ]),
        MAPPING,
    )
    assert result.summary["processed_ok"] == 1
    assert result.summary["errors"] == 0
    assert result.metrics[0].aduno_id == "ADN-HOST-0001"
    assert result.metrics[0].data["usage_percent"] == 78.5


def test_pipeline_empty_hostname_rejected():
    """An entry with an empty hostname must be rejected and recorded as an error."""
    result = process_metrics(
        _make_raw_input([
            {"host": "", "metric_type": "cpu", "values": {"usage_percent": "45"}, "tags": {}},
        ]),
        MAPPING,
    )
    assert result.summary["processed_ok"] == 0
    assert result.summary["errors"] == 1
    assert "Leerer Hostname" in result.errors[0].reason


def test_partial_field_error_metric_still_processed():
    """A metric with one non-numeric field is still processed; only that field is dropped."""
    errors: list[ErrorEntry] = []
    data, _ = convert_values(
        {"usage_percent": "ERROR_READ", "cores": "32"}, "host", "cpu", errors
    )
    assert "usage_percent" not in data
    assert data["cores"] == 32
    assert len(errors) == 1
    assert errors[0].reason == "Nicht-numerischer Wert"


def test_threshold_alert_triggered():
    """A CPU temperature above 80 °C must produce a critical alert."""
    metric = ProcessedMetric(
        aduno_id="ADN-HOST-0002",
        hostname="esx-prod-02",
        type="temperature",
        data={"cpu_temp_celsius": 82},
    )
    alerts = check_thresholds(metric)
    assert len(alerts) == 1
    assert alerts[0].type == "cpu_temp_critical"
    assert alerts[0].severity == "critical"

