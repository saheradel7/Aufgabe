"""
parser/alerts.py – Threshold checks that produce Alert objects.
"""

from .models import Alert, ProcessedMetric
from .utils import bytes_to_human


def check_thresholds(metric: ProcessedMetric) -> list[Alert]:
    """
    Evaluate *metric* against pre-defined thresholds and return any alerts.

    Thresholds:
      cpu   usage_percent > 90       → warning
      memory used/total   > 85 %     → warning
      memory swap_used    > 1 GB     → warning
      temperature cpu_temp > 80 °C   → critical
      disk    free/capacity < 10 %   → critical
      network errors_in/out > 0      → info
    """
    alerts: list[Alert] = []
    data = metric.data
    aduno_id = metric.aduno_id

    match metric.type:
        case "cpu":
            _check_cpu(aduno_id, data, alerts)
        case "memory":
            _check_memory(aduno_id, data, alerts)
        case "temperature":
            _check_temperature(aduno_id, data, alerts)
        case "disk":
            _check_disk(aduno_id, data, alerts)
        case "network":
            _check_network(aduno_id, data, alerts)

    return alerts


# ---------------------------------------------------------------------------
# Private per-type helpers
# ---------------------------------------------------------------------------


def _check_cpu(aduno_id: str, data: dict, alerts: list[Alert]) -> None:
    usage = data.get("usage_percent")
    if isinstance(usage, (int, float)) and usage > 90:
        alerts.append(
            Alert(
                aduno_id=aduno_id,
                type="cpu_usage_high",
                severity="warning",
                message=f"Hohe CPU-Auslastung bei {usage}%",
                threshold=90.0,
            )
        )


def _check_memory(aduno_id: str, data: dict, alerts: list[Alert]) -> None:
    total = data.get("total_bytes")
    used = data.get("used_bytes")
    swap = data.get("swap_used_bytes")

    if isinstance(total, (int, float)) and isinstance(used, (int, float)) and total > 0:
        pct = used / total * 100
        if pct > 85:
            alerts.append(
                Alert(
                    aduno_id=aduno_id,
                    type="memory_usage_high",
                    severity="warning",
                    message=f"RAM-Auslastung bei {pct:.1f}%",
                    threshold=85.0,
                )
            )

    if isinstance(swap, (int, float)) and swap > 1_073_741_824:
        alerts.append(
            Alert(
                aduno_id=aduno_id,
                type="swap_usage_high",
                severity="warning",
                message=f"Erhöhter Swap-Verbrauch: {bytes_to_human(swap)}",
                threshold=1_073_741_824,
            )
        )


def _check_temperature(aduno_id: str, data: dict, alerts: list[Alert]) -> None:
    temp = data.get("cpu_temp_celsius")
    if isinstance(temp, (int, float)) and temp > 80:
        alerts.append(
            Alert(
                aduno_id=aduno_id,
                type="cpu_temp_critical",
                severity="critical",
                message=f"CPU-Temperatur bei {temp}°C",
                threshold=80,
            )
        )


def _check_disk(aduno_id: str, data: dict, alerts: list[Alert]) -> None:
    capacity = data.get("capacity_bytes")
    free = data.get("free_bytes")
    datastore = data.get("datastore_name", "unknown")

    if isinstance(capacity, (int, float)) and isinstance(free, (int, float)) and capacity > 0:
        free_pct = free / capacity * 100
        if free_pct < 10:
            alerts.append(
                Alert(
                    aduno_id=aduno_id,
                    type="disk_usage_high",
                    severity="critical",
                    message=f"Datastore {datastore} nur noch {free_pct:.1f}% frei",
                    threshold=10.0,
                )
            )


def _check_network(aduno_id: str, data: dict, alerts: list[Alert]) -> None:
    errors_in = data.get("errors_in", 0)
    errors_out = data.get("errors_out", 0)
    if (isinstance(errors_in, (int, float)) and errors_in > 0) or (
        isinstance(errors_out, (int, float)) and errors_out > 0
    ):
        alerts.append(
            Alert(
                aduno_id=aduno_id,
                type="network_errors_detected",
                severity="info",
                message=f"Netzwerk-Fehler erkannt (in={errors_in}, out={errors_out})",
                threshold=0,
            )
        )
