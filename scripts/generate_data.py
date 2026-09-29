#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/generate_data.py

CLI entry point for the Phase 2 synthetic demand generator.

Run from the project root:

    python scripts/generate_data.py --seed 42 --days 7

All output files are written to data/synthetic/ and clearly marked
DATA_TYPE = SYNTHETIC.  See data_generation/README.md for full methodology.

Options
-------
--seed INT      Random seed (default: 42). Same seed → identical outputs.
--days INT      Number of days to generate (default: 7, Mon–Sun).
--start DATE    Start date ISO format YYYY-MM-DD (default: 2024-01-08 = Monday).
--output DIR    Output directory (default: data/synthetic).
--holiday DATE  Mark a date as holiday (repeatable).
--event DATE    Mark a date as event-day (repeatable).
--quiet         Suppress INFO logging.
"""
import argparse
import io
import json
import logging
import sys
from datetime import date
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.demand.pipeline import DemandConfig, DemandPipeline
from src.config.settings import LOG_FORMAT


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate synthetic Bengaluru Metro passenger demand data."
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--days", type=int, default=7, help="Days to generate (default: 7)")
    parser.add_argument("--start", type=str, default="2024-01-08",
                        help="Start date YYYY-MM-DD (default: 2024-01-08)")
    parser.add_argument("--output", type=str, default="data/synthetic",
                        help="Output directory (default: data/synthetic)")
    parser.add_argument("--holiday", action="append", default=[],
                        help="Mark date as holiday (repeatable)")
    parser.add_argument("--event", action="append", default=[],
                        help="Mark date as event-day (repeatable)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress INFO logging")
    return parser.parse_args()


def main():
    args = parse_args()
    log_level = logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(level=log_level, format=LOG_FORMAT)
    logger = logging.getLogger(__name__)

    try:
        start = date.fromisoformat(args.start)
    except ValueError as exc:
        print(f"ERROR: Invalid start date '{args.start}': {exc}")
        sys.exit(1)

    config = DemandConfig(
        seed=args.seed,
        start_date=start,
        num_days=args.days,
        holiday_dates=args.holiday,
        event_dates=args.event,
        output_dir=Path(args.output),
    )

    print("\n" + "=" * 60)
    print("  NAMMA PULSE -- SYNTHETIC DATA GENERATOR")
    print("=" * 60)
    print(f"  DATA_TYPE    : SYNTHETIC")
    print(f"  Seed         : {config.seed}")
    print(f"  Date range   : {config.start_date} + {config.num_days} days")
    print(f"  Output dir   : {config.output_dir}")
    print(f"  Holidays     : {config.holiday_dates or 'none'}")
    print(f"  Event days   : {config.event_dates or 'none'}")
    print()

    pipeline = DemandPipeline(config)
    pipeline.initialise()

    print("  Generating demand data...")
    tables = pipeline.run()

    print("  Writing output files...")
    pipeline.write_outputs(tables)

    print("  Computing summary statistics...")
    summary = pipeline.generate_summary(tables)

    print()
    print("  Summary")
    print("  " + "-" * 56)
    print(f"  Total synthetic passengers  : {summary['total_synthetic_passengers']:,}")
    print(f"  OD demand rows              : {summary['num_od_rows']:,}")
    print(f"  Edge load rows              : {summary['num_edge_rows']:,}")
    print(f"  Congestion rows             : {summary['num_congestion_rows']:,}")
    print(f"  Delay events                : {summary['num_delay_events']:,}")
    print(f"  Avg peak congestion         : {summary['avg_peak_congestion_pct']:.1f}%")
    print(f"  Avg off-peak congestion     : {summary['avg_offpeak_congestion_pct']:.1f}%")
    print(f"  Max congestion              : {summary['max_congestion_pct']:.1f}%")
    print(f"  Weekday demand              : {summary['weekday_total']:,}")
    print(f"  Weekend demand              : {summary['weekend_total']:,}")
    print()
    print("  Top 5 busiest stations:")
    for item in summary["top_5_busiest_stations"]:
        print(f"    {item['station_id']:6s}  {item['total_arrivals']:>10,} arrivals")
    print()
    print("  [PASS] Generation complete.")
    print("=" * 60 + "\n")

    # Write summary JSON
    summary_path = config.output_dir / "generation_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"  Summary written to {summary_path}")


if __name__ == "__main__":
    main()
