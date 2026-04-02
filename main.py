"""
main.py – CLI entry point for the aduno® Metric Parser.

Usage:
    python main.py
    python main.py --input data/metrics_raw.json --mapping data/host_mapping.json --output output.json
"""

import argparse
import json
import logging
from pathlib import Path

from parser.pipeline import load_host_mapping, load_raw_input, process_metrics

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="aduno® Metric Parser")
    p.add_argument("--input",   default="data/metrics_raw.json",  help="metrics_raw.json path")
    p.add_argument("--mapping", default="data/host_mapping.json", help="host_mapping.json path")
    p.add_argument("--output",  default="output.json",            help="output file path")
    return p.parse_args()


def main() -> None:
    """Load, process, and write results to the output file."""
    args = parse_args()

    raw_input    = load_raw_input(Path(args.input))
    host_mapping = load_host_mapping(Path(args.mapping))
    result       = process_metrics(raw_input, host_mapping)

    output_path = Path(args.output)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(result.model_dump(), fh, indent=2, ensure_ascii=False)

    log.info(
        "Done → %s  (processed=%d  errors=%d  alerts=%d)",
        output_path,
        result.summary["processed_ok"],
        result.summary["errors"],
        result.summary["alerts_generated"],
    )


if __name__ == "__main__":
    main()
