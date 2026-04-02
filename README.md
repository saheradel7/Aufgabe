# aduno® Monitoring-Daten Parser

A Python parser for raw monitoring metrics (ESXi, SNMP, IPMI). It validates,
normalises, enriches with `aduno_id`, checks thresholds, and writes a structured
`output.json`.

---

## Project structure

```
Aufgabe/
├── parser/               ← Python package
│   ├── __init__.py
│   ├── models.py         – Pydantic models + constants
│   ├── utils.py          – bytes_to_human, resolve_aduno_id, convert_values
│   ├── alerts.py         – check_thresholds (per metric type)
│   └── pipeline.py       – load_raw_input, load_host_mapping, process_metrics
├── tests/
│   └── test_metric_parser.py
├── data/
│   ├── metrics_raw.json  ← input
│   └── host_mapping.json ← input
├── main.py               ← CLI entry point
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Requirements

- Python 3.12+ (or Docker)
- pydantic v2
- pytest (tests only)

---

## Run with Docker (recommended)

```bash
# Build image, run parser → output.json written to project root
docker compose run --rm parser

# Run the test suite
docker compose run --rm tests
```

---

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run parser (defaults: data/metrics_raw.json → output.json)
python3 main.py

# Custom paths
python3 main.py --input data/metrics_raw.json \
                --mapping data/host_mapping.json \
                --output output.json

# Run tests
pytest tests/ -v
```

---

## Design decisions

| Topic | Decision |
|---|---|
| **Package layout** | Logic split into `models`, `utils`, `alerts`, `pipeline` — single-responsibility, easy to test in isolation. |
| **Pydantic v2** | `RawMetric` validates host + metric_type at parse time; field errors are collected, never crash the pipeline. |
| **Partial errors** | A metric with one bad field (e.g. `ERROR_READ`) is still processed — only that field is dropped and an `ErrorEntry` is recorded. |
| **Text labels** | `STRING_FIELDS` (datastore_name, interface) pass through unchanged; only measurement fields are converted/validated. |
| **Byte conversion** | `BYTE_FIELDS` set drives human-readable conversion — no heuristic string matching. |
| **Unknown hosts** | Deterministic `ADN-HOST-UNKNOWN-{sha256[:8]}` ID ensures idempotent re-runs. |
| **Logging** | Standard `logging` at INFO level; swap `basicConfig` for file/JSON handler without touching business logic. |
| **Docker** | Single `Dockerfile` + two `docker-compose` services (`parser`, `tests`) for easy local and CI use. |
