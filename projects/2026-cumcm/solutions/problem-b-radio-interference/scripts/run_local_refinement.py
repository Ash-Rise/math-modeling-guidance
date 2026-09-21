"""Build compact synthetic evidence for one certified follow-up after Q2.

This is a deterministic geometry audit, not an official simulator experiment or
a probability model. Run from the solution directory:
python scripts/run_local_refinement.py --output results/local_refinement_evidence.json
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from local_refinement import local_probe_options
from radio_geometry import Bearing, unit
from second_point import synthetic_reply, two_bearing_region


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    first = Bearing((0.0, 0.0), 0.0)
    second = np.array([550.0, 575.0])
    distances = [20.001, 100.0, 300.0, 600.0, 900.0, 1200.0, 1500.0]
    first_offsets = [-1.0, 0.0, 1.0]
    second_errors = [-1.0, 0.0, 1.0]
    cases = []

    for distance in distances:
        for offset in first_offsets:
            truth = distance * unit(offset)
            source_radius = max(1000.0, distance)
            for second_error in second_errors:
                reply = synthetic_reply(truth, source_radius, second, second_error)
                assert reply["result"] == "direction"
                prior = two_bearing_region(first, second, reply["degrees"])
                assert prior.contains(truth)
                prior_radius = prior.enclosing_circle().radius_upper
                row = {
                    "distance_m": distance,
                    "first_true_offset_degrees": offset,
                    "second_error_degrees": second_error,
                    "second_report_degrees": reply["degrees"],
                    "radius_after_two_readings_m": prior_radius,
                }
                if prior_radius <= 20.0:
                    row["status"] = "clear_after_two"
                else:
                    options = local_probe_options(
                        prior,
                        second,
                        radii=(150.0, 300.0, 500.0),
                        directions=12,
                        move_budget=700.0,
                        bin_degrees=5.0,
                    )
                    chosen = options["best_with_supplied_budget"]
                    if chosen is None:
                        row["status"] = "no_candidate_in_finite_design"
                    else:
                        assert chosen["reception_margin_m"] >= -1e-6
                        row.update({
                            "status": "clear_after_next_normal_reply"
                            if chosen["radius_upper_m"] <= 20.0 else "needs_more_evidence",
                            "probe_position": chosen["position"],
                            "probe_move_m": chosen["move_m"],
                            "probe_move_and_measure_s": chosen["move_and_measure_s"],
                            "probe_reception_margin_m": chosen["reception_margin_m"],
                            "certified_next_radius_upper_m": chosen["radius_upper_m"],
                        })
                cases.append(row)

    counts = {status: sum(row["status"] == status for row in cases) for status in sorted({row["status"] for row in cases})}
    probe_cases = [row for row in cases if "certified_next_radius_upper_m" in row]
    result = {
        "scope": "Deterministic synthetic geometry evidence; not official simulator performance",
        "runtime": {
            "python": sys.version.split()[0],
            "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy")},
        },
        "design": {
            "first_position": [0.0, 0.0],
            "first_report_degrees": 0.0,
            "second_position": second.tolist(),
            "distances_m": distances,
            "first_true_offsets_degrees": first_offsets,
            "second_error_degrees": second_errors,
            "follow_up_finite_design": {
                "offset_radii_m": [150.0, 300.0, 500.0],
                "directions": 12,
                "move_budget_m": 700.0,
                "response_bin_degrees": 5.0,
            },
            "contract": "Every retained follow-up is within 1000 m of the full current enclosure. Each 5-degree response bin is enlarged by its 2.5-degree half-width before the next enclosing radius is computed.",
        },
        "summary": {
            "cases": len(cases),
            "status_counts": counts,
            "max_radius_after_two_readings_m": max(row["radius_after_two_readings_m"] for row in cases),
            "max_certified_next_radius_upper_m": max((row["certified_next_radius_upper_m"] for row in probe_cases), default=None),
            "max_selected_probe_move_m": max((row["probe_move_m"] for row in probe_cases), default=None),
            "min_selected_reception_margin_m": min((row["probe_reception_margin_m"] for row in probe_cases), default=None),
        },
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
