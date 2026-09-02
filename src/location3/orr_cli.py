"""Preview and fetch ORR operator performance for a private run: two bounded calls."""

from __future__ import annotations

import argparse
from datetime import timedelta
import json
from pathlib import Path
from typing import Any, Sequence

from .cache import CachingTransport, RequestLedger
from .net import HttpTransport, UrllibTransport
from .orr import MAX_OPERATORS, OrrPerformanceAdapter, validate_performance
from .schema_validation import validate_schema_document


OUTPUT_NAME = "orr-performance.json"


def main(argv: Sequence[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description=(
            "Fetch ORR punctuality and cancellation figures for named train operators "
            "into a private run (two bounded calls, cached for seven days)"
        )
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument(
        "--operator", action="append", default=[], metavar="NAME",
        help="an operator exactly as ORR names it, for example 'Chiltern Railways'",
    )
    parser.add_argument("--cache", type=Path, default=root / "cache")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    if not args.run_dir.is_dir() or not (args.run_dir / "results.json").exists():
        parser.error("run-dir must be an existing research run")
    if not args.operator:
        parser.error("at least one --operator is required")
    if len(args.operator) > MAX_OPERATORS:
        parser.error(f"at most {MAX_OPERATORS} operators per fetch")

    adapter = OrrPerformanceAdapter()
    output = args.run_dir / OUTPUT_NAME
    print("ORR fetch plan: operator-level punctuality (Table 3138) and cancellations (Table 3124)")
    for name, url in adapter.table_urls().items():
        print(f"Fetched from ORR ({name}): {url}")
    print(f"Operators matched locally after download: {', '.join(args.operator)}")
    print("Sent to ORR: only the two public table URLs; no run data, origin, or operator names leave the machine")
    print("Maximum live provider calls: 2 (a seven-day cache hit makes none)")
    print(f"Private output: {output}")
    if not args.execute:
        print("Preview only. Re-run with --execute after reviewing this disclosure.")
        return 0

    performance = fetch_performance(
        args.run_dir, args.operator, cache_directory=args.cache
    )
    for record in performance["operators"]:
        print(
            f"{record['operator']}: {record['period']}; time to 3 "
            f"{record['punctuality_time_to_3_annual_percent']:.1f}% (annual average), "
            f"cancellations {record['cancellations_annual_percent']:.1f}% (annual average)"
        )
    print(
        f"Wrote {output}; {performance['request_ledger_summary']['network_requests']} live "
        f"calls, {performance['request_ledger_summary']['cache_hits']} cache hits"
    )
    return 0


def fetch_performance(
    run_dir: Path,
    operators: Sequence[str],
    *,
    cache_directory: Path,
    transport: HttpTransport | None = None,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    ledger = RequestLedger(max_network_requests=2)
    caching = CachingTransport(
        "orr", transport or UrllibTransport(), cache_directory, ledger, ttl=timedelta(days=7)
    )
    performance = OrrPerformanceAdapter(transport=caching).fetch(
        operators, retrieved_at=retrieved_at
    )
    performance["request_ledger"] = ledger.entries
    performance["request_ledger_summary"] = {
        "network_requests": ledger.network_requests,
        "cache_hits": sum(entry["cache"] == "hit" for entry in ledger.entries),
    }
    validate_performance(performance)
    validate_schema_document(performance, "orr-performance.schema.json")
    (run_dir / OUTPUT_NAME).write_text(
        json.dumps(performance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return performance
