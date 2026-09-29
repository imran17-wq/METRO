#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/expand_synthetic_data.py

Generates 30 days of synthetic data (2024-01-01 to 2024-01-30, seed=42)
specifically for ML model training and evaluation.

Saves files to data/synthetic/*_30d.csv so that original 7-day files
remain untouched.
"""
import io
import json
import logging
import sys
from datetime import date
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.demand.pipeline import DemandConfig, DemandPipeline, _write_csv
from src.config.settings import LOG_FORMAT, DATA_DIR

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    
    out_dir = DATA_DIR / "synthetic"
    config = DemandConfig(
        seed=42,
        start_date=date(2024, 1, 1),
        num_days=30,
        output_dir=out_dir,
    )

    print("\n" + "=" * 60)
    print("  NAMMA PULSE -- 30-DAY SYNTHETIC DATA EXPANSION (ML)")
    print("=" * 60)
    print(f"  DATA_TYPE    : SYNTHETIC")
    print(f"  Seed         : {config.seed}")
    print(f"  Date range   : {config.start_date} to {config.start_date + date.resolution * 29} (30 days)")
    print(f"  Output dir   : {config.output_dir}")
    print()

    pipeline = DemandPipeline(config)
    pipeline.initialise()

    print("  Generating 30-day demand data...")
    tables = pipeline.run()

    print("  Writing *_30d.csv output files...")
    _write_csv(
        out_dir / "od_demand_30d.csv",
        tables["od_demand"],
        ["date", "time_slot", "slot_start", "origin_id", "origin_name",
         "destination_id", "destination_name", "demand", "day_type", "data_type"],
    )
    _write_csv(
        out_dir / "edge_load_30d.csv",
        tables["edge_load"],
        ["date", "time_slot", "slot_start", "edge_id", "from_id", "to_id",
         "line", "flow_passengers", "capacity", "congestion_pct",
         "congestion_band", "day_type", "data_type"],
    )
    _write_csv(
        out_dir / "congestion_30d.csv",
        tables["congestion"],
        ["date", "time_slot", "slot_start", "station_id", "station_name",
         "line", "congestion_pct", "congestion_band", "day_type", "data_type"],
    )
    _write_csv(
        out_dir / "delay_events_30d.csv",
        tables["delay_events"],
        ["date", "time_slot", "slot_start", "edge_id", "from_id", "to_id",
         "line", "delay_min", "cause", "congestion_band",
         "is_interchange_edge", "day_type", "data_type"],
    )
    _write_csv(
        out_dir / "station_demand_30d.csv",
        tables["station_demand"],
        ["date", "station_id", "station_name", "line",
         "total_arrivals", "total_departures", "net_flow", "day_type", "data_type"],
    )

    summary = pipeline.generate_summary(tables)
    summary_path = out_dir / "generation_summary_30d.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print()
    print("  30-Day Expansion Summary")
    print("  " + "-" * 56)
    print(f"  Total synthetic passengers  : {summary['total_synthetic_passengers']:,}")
    print(f"  OD demand rows              : {summary['num_od_rows']:,}")
    print(f"  Edge load rows              : {summary['num_edge_rows']:,}")
    print(f"  Congestion rows             : {summary['num_congestion_rows']:,}")
    print(f"  Delay events                : {summary['num_delay_events']:,}")
    print(f"  Avg peak congestion         : {summary['avg_peak_congestion_pct']:.1f}%")
    print(f"  Avg off-peak congestion     : {summary['avg_offpeak_congestion_pct']:.1f}%")
    print()
    print("  [PASS] 30-day synthetic dataset successfully created.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
