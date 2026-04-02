"""Threshold checks: evaluate a processed metric and return any alerts."""

from .models import Alert, ProcessedMetric
from .utils import bytes_to_human


def _num(data: dict, key: str) -> float | None:
    """Return data[key] if it is a number, otherwise None."""
    val = data.get(key)
    return val if isinstance(val, (int, float)) else None


def check_thresholds(metric: ProcessedMetric) -> list[Alert]:
    """Return alerts for any threshold violations found in *metric*."""
    alerts: list[Alert] = []
    data = metric.data
    aid = metric.aduno_id  # short alias used throughout

    match metric.type:

        case "cpu":
            usage = _num(data, "usage_percent")
            if usage is not None and usage > 90:
                alerts.append(Alert(aduno_id=aid, type="cpu_usage_high", severity="warning",
                                    message=f"Hohe CPU-Auslastung bei {usage}%", threshold=90.0))

        case "memory":
            total, used = _num(data, "total_bytes"), _num(data, "used_bytes")
            swap = _num(data, "swap_used_bytes")

            if total and used is not None:
                pct = used / total * 100
                if pct > 85:
                    alerts.append(Alert(aduno_id=aid, type="memory_usage_high", severity="warning",
                                        message=f"RAM-Auslastung bei {pct:.1f}%", threshold=85.0))

            if swap is not None and swap > 1_073_741_824:
                alerts.append(Alert(aduno_id=aid, type="swap_usage_high", severity="warning",
                                    message=f"Erhöhter Swap-Verbrauch: {bytes_to_human(swap)}",
                                    threshold=1_073_741_824))

        case "temperature":
            temp = _num(data, "cpu_temp_celsius")
            if temp is not None and temp > 80:
                alerts.append(Alert(aduno_id=aid, type="cpu_temp_critical", severity="critical",
                                    message=f"CPU-Temperatur bei {temp}°C", threshold=80))

        case "disk":
            capacity, free = _num(data, "capacity_bytes"), _num(data, "free_bytes")
            datastore = data.get("datastore_name", "unknown")

            if capacity and free is not None:
                free_pct = free / capacity * 100
                if free_pct < 10:
                    alerts.append(Alert(aduno_id=aid, type="disk_usage_high", severity="critical",
                                        message=f"Datastore {datastore} nur noch {free_pct:.1f}% frei",
                                        threshold=10.0))

        case "network":
            errors_in  = _num(data, "errors_in")  or 0
            errors_out = _num(data, "errors_out") or 0
            if errors_in > 0 or errors_out > 0:
                alerts.append(Alert(aduno_id=aid, type="network_errors_detected", severity="info",
                                    message=f"Netzwerk-Fehler erkannt (in={errors_in}, out={errors_out})",
                                    threshold=0))

    return alerts
