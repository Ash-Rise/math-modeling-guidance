"""Run deterministic offline Q3/Q4 stress cases under the published rules.

The output is evidence for algorithm contracts and cost scale, not official
simulator performance and not a probability estimate for hidden cases.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mission import run_mission
from offline_simulator import OfflineArena, Source
from radio_geometry import unit


def scenario(mode: str, count: int, seed: int, *, boundary: bool) -> list[Source]:
    rng = np.random.default_rng(seed)
    channels = rng.choice(np.arange(1, 21), size=count, replace=False)
    rows = []
    for index, channel in enumerate(channels):
        if boundary:
            angle = 360.0 * index / count
            radius_from_origin = 1800.0 if index % 2 == 0 else 1700.0
        else:
            angle = rng.uniform(0.0, 360.0)
            radius_from_origin = 1800.0 * math.sqrt(rng.uniform())
        position = radius_from_origin * unit(angle)
        reception = float(rng.uniform(1000.0, 1500.0))
        if mode == "q3":
            direction = None
        elif index == 0:
            direction = None  # Q4 cases contain both types.
        elif boundary:
            direction = angle  # outward-facing boundary stress.
        else:
            direction = float(rng.uniform(0.0, 360.0))
        rows.append(Source(int(channel), tuple(position), reception, direction))
    return rows


def summarize(rows: list[dict]) -> dict:
    fields = ("cleared_ratio", "virtual_time_s", "average_clear_time_s",
              "program_runtime_s", "measure_requests", "clear_requests", "failed_clears")
    return {field: {
        "min": float(np.min([row[field] for row in rows])),
        "median": float(np.median([row[field] for row in rows])),
        "max": float(np.max([row[field] for row in rows])),
    } for field in fields}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    design = [(10, 0, False)] if args.pilot else [
        (count, replicate, replicate == 0)
        for count in (10, 13, 16) for replicate in range(4)
    ]
    all_rows = []
    started = time.perf_counter()
    for mode_index, mode in enumerate(("q3", "q4")):
        for count, replicate, boundary in design:
            seed = 20260920 + 1000 * mode_index + 100 * count + replicate
            arena = OfflineArena(scenario(mode, count, seed, boundary=boundary), error_seed=seed)
            mission = run_mission(arena, mode)
            if arena.cleared_sources != arena.total_sources:
                raise AssertionError(f"{mode} seed {seed} did not clear all sources")
            if mission.virtual_time_s > 360000.0:
                raise AssertionError(f"{mode} seed {seed} exceeded virtual limit")
            row = mission.to_dict()
            row.update({
                "seed": seed,
                "source_count": count,
                "boundary_stress": boundary,
                "cleared_count": arena.cleared_sources,
                "cleared_ratio": arena.cleared_sources / arena.total_sources,
                "average_clear_time_s": mission.virtual_time_s / arena.cleared_sources,
            })
            all_rows.append(row)
            print(f"{mode} n={count} r={replicate}: {mission.virtual_time_s:.2f}s, "
                  f"wall={mission.program_runtime_s:.2f}s", flush=True)
    result = {
        "scope": "Deterministic offline stress evidence under published rules; not official simulator performance",
        "runtime": {
            "python": sys.version.split()[0],
            "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy")},
            "elapsed_seconds": time.perf_counter() - started,
        },
        "design": {
            "cases_per_mode": len(design),
            "counts": sorted({row[0] for row in design}),
            "replicates_per_count": 1 if args.pilot else 4,
            "boundary_replicate": "replicate 0 uses alternating 1700/1800 m radii; Q4 directional sources face outward",
            "random_replicates": "uniform area positions, uniform reception radii and Q4 directions; seeded construction only, not a hidden-distribution model",
        },
        "summary": {mode: summarize([row for row in all_rows if row["mode"] == mode])
                    for mode in ("q3", "q4")},
        "cases": all_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
