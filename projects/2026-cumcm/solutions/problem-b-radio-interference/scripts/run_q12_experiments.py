"""Reproduce Q1/Q2 evidence. No official simulator, stochastic model prior, or Q3 search.

Run from this solution directory: python scripts/run_q12_experiments.py --output results/q12_evidence.json
The parameter/scenario grids are experimental designs, not source/error distributions.
"""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
from scipy.spatial.distance import pdist
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from radio_geometry import Bearing, Disk, localization_region, point, unit
from second_point import local_point, pareto_indices, reception_margin, response_diameter_upper, synthetic_reply, two_bearing_region


def polygon_oracle(observations, sides, outer):
    """Independent GEOS intersection of nested circle approximations and exact wedge triangles."""
    angles = np.arange(sides) * 2 * math.pi / sides
    directions = np.column_stack((np.cos(angles), np.sin(angles)))

    def disk(center, radius):
        radius = radius / math.cos(math.pi / sides) if outer else radius
        return Polygon(point(center) + radius * directions)

    shape = disk((0, 0), 1800)
    for obs in observations:
        s = point(obs.position)
        length = 2 * (np.linalg.norm(s) + 1800) / math.cos(math.radians(obs.error_degrees))
        triangle = Polygon([s, s + length * unit(obs.degrees - obs.error_degrees),
                            s + length * unit(obs.degrees + obs.error_degrees)])
        shape = shape.intersection(triangle).intersection(disk(s, 1500))
    if shape.is_empty:
        return 0.0, 0.0
    hull = shape.convex_hull
    coords = np.asarray(hull.exterior.coords)[:-1] if hull.geom_type == "Polygon" else np.asarray(hull.coords)
    return (float(np.max(pdist(coords))) if len(coords) > 1 else 0.0), float(shape.area)


def geometry_evidence():
    rng = np.random.default_rng(20260910)
    checks, certified, max_gap, worst_area_gap = 0, 0, 0., 0.
    oracle_cases = []
    for case in range(60):
        angle = rng.uniform(0, 2 * math.pi)
        radius = 1800 if case % 6 == 0 else rng.uniform(0, 1750)
        truth = radius * np.array([math.cos(angle), math.sin(angle)])
        observations = []
        for step in range(1 + case % 5):
            bearing = rng.uniform(0, 360)
            distance = rng.uniform(6, 1490)
            s = truth - distance * unit(bearing)
            error = (-1., 1., 0.)[(case + step) % 3]
            reply = synthetic_reply(truth, 1500, s, error)
            observations.append(Bearing(tuple(s), reply["degrees"]))
            region = localization_region(observations, reception_bound=1500)
            assert region.status == "bounded" and region.contains(truth)
            checks += 1
            circle = region.enclosing_circle()
            assert np.linalg.norm(truth - circle.center) <= circle.radius_upper + 1e-8
            if circle.clearance() == "guaranteed":
                certified += 1
                assert np.linalg.norm(truth - circle.center) <= 20
        if case < 24:
            exact_diameter, exact_area = region.diameter().value, region.area()
            rows = []
            for sides in (128, 512):
                lower_d, lower_a = polygon_oracle(observations, sides, False)
                upper_d, upper_a = polygon_oracle(observations, sides, True)
                assert lower_d <= exact_diameter + 2e-5 <= upper_d + 4e-5
                assert lower_a <= exact_area + 1e-3 <= upper_a + 2e-3
                rows.append({"sides": sides, "diameter_lower_m": lower_d,
                             "diameter_upper_m": upper_d, "area_lower_m2": lower_a, "area_upper_m2": upper_a})
            max_gap = max(max_gap, rows[-1]["diameter_upper_m"] - rows[-1]["diameter_lower_m"])
            worst_area_gap = max(worst_area_gap, rows[-1]["area_upper_m2"] - rows[-1]["area_lower_m2"])
            oracle_cases.append({"id": case, "truth": truth.tolist(),
                                 "observations": [{"position": list(o.position), "degrees": o.degrees} for o in observations],
                                 "diameter_m": exact_diameter, "area_m2": exact_area, "independent_bounds": rows})
    return {"seed": 20260910, "constructed_cases": 60, "legal_updates": checks,
            "truth_containment_failures": 0, "guaranteed_clearance_checks": certified,
            "false_clearance_certificates": 0, "oracle_cases": oracle_cases,
            "max_512_side_diameter_bracket_width_m": max_gap,
            "max_512_side_area_bracket_width_m2": worst_area_gap}


def scenario_scan(forwards, laterals, distances, offsets, errors, *, candidates=None, controls=True):
    first = Bearing((0., 0.), 0.)
    records = []
    if candidates is None:
        candidates = [(a, b) for a in forwards for b in laterals
                      if reception_margin(first, (a, b)) >= 0]
    # Keep the old analytical candidate and two informative controls.
    candidates = list(dict.fromkeys(candidates + ([(750., 500.), (0., 500.), (0., 0.)] if controls else [])))
    for number, (a, b) in enumerate(candidates):
        q = np.array([a, b])
        diameters, radii, areas = [], [], []
        loss, near, updates, certified, radius_trials, worst = 0, 0, 0, 0, 0, None
        for distance in distances:
            for offset in offsets:
                truth = distance * unit(offset)
                actual_min_r = max(1000., distance)
                # Reception depends on R, while the estimator is never given its value.
                for radius in sorted(set([actual_min_r, (actual_min_r + 1500) / 2, 1500.])):
                    reply = synthetic_reply(truth, radius, q, 0.)
                    radius_trials += 1
                    loss += reply["result"] == "no_signal"
                # Evaluate geometry at the least favorable compatible radius.
                for error in errors:
                    error = -offset if a == b == 0 else error  # fixed error at repeated location
                    reply = synthetic_reply(truth, actual_min_r, q, error)
                    if reply["result"] == "no_signal":
                        continue
                    if reply["result"] == "near":
                        near += 1
                        assert np.linalg.norm(truth - q) <= 5 + 1e-8
                        continue
                    region = two_bearing_region(first, q, reply["degrees"])
                    assert region.status == "bounded" and region.contains(truth)
                    updates += 1
                    diameter, area, circle = region.diameter().value, region.area(), region.enclosing_circle()
                    assert np.linalg.norm(truth - circle.center) <= circle.radius_upper + 1e-8
                    if circle.clearance() == "guaranteed":
                        certified += 1
                        assert np.linalg.norm(truth - circle.center) <= 20
                    if not diameters or diameter > max(diameters):
                        worst = {"distance_m": float(distance), "first_true_offset_degrees": float(offset),
                                 "requested_second_error_degrees": float(error),
                                 "actual_second_error_degrees": float((reply["degrees"] - math.degrees(math.atan2(*(truth-q)[::-1])) + 180) % 360 - 180),
                                 "second_report_degrees": reply["degrees"],
                                 "truth": truth.tolist(), "diameter_m": diameter,
                                 "enclosing_center": circle.center.tolist(), "enclosing_radius_upper_m": circle.radius_upper}
                    diameters.append(diameter)
                    radii.append(circle.radius_upper)
                    areas.append(area)
        move = math.hypot(a, b)
        records.append({"forward_m": float(a), "lateral_m": float(b), "move_m": move,
                        "move_and_second_measure_s": move / 5 + 5,
                        "reception_margin_m": float(reception_margin(first, q)),
                        "universal_reception": bool(reception_margin(first, q) >= 0),
                        "radius_trials": radius_trials, "no_signal_trials": int(loss),
                        "legal_direction_updates": updates, "near_trials": near,
                        "guaranteed_clearance_checks": certified,
                        "sample_max_diameter_m": max(diameters),
                        "sample_median_diameter_m": float(np.median(diameters)),
                        "sample_max_radius_upper_m": max(radii),
                        "sample_median_radius_upper_m": float(np.median(radii)),
                        "sample_median_area_m2": float(np.median(areas)), "worst_case": worst})
        if number % 12 == 0:
            print(f"Q2 candidate {number + 1}/{len(candidates)}", flush=True)
    valid = [r for r in records if r["universal_reception"] and r["move_m"] > 0]
    frontier = [valid[i] for i in pareto_indices(valid)]
    frontier.sort(key=lambda r: r["move_m"])
    return records, [{k: r[k] for k in ("forward_m", "lateral_m", "move_m", "sample_max_diameter_m",
                                      "sample_median_diameter_m", "sample_max_radius_upper_m")} for r in frontier]


def refinement_evidence(coarse, distances, offsets, errors):
    """Local refinement tests whether the coarse recommendation survives denser designs."""
    first = Bearing((0., 0.), 0.)
    budgets = [600., 800., 1000.]  # comparison axes, not official objectives or hidden weights
    candidates = []
    for budget in budgets:
        best = min((r for r in coarse if r["universal_reception"] and 0 < r["move_m"] <= budget),
                   key=lambda r: r["sample_max_diameter_m"])
        for a in np.arange(best["forward_m"] - 100, best["forward_m"] + 101, 25):
            for b in np.arange(best["lateral_m"] - 100, best["lateral_m"] + 101, 25):
                if math.hypot(a, b) <= budget and reception_margin(first, (a, b)) >= 0:
                    candidates.append((a, b))
    candidates = list(dict.fromkeys(candidates))
    local_rows, _ = scenario_scan([], [], distances, offsets, errors, candidates=candidates, controls=False)
    evaluated, chosen = {}, []
    for budget in budgets:
        finalists = sorted((r for r in local_rows + coarse if r["universal_reception"] and 0 < r["move_m"] <= budget),
                          key=lambda r: r["sample_max_diameter_m"])[:5]
        for row in finalists:
            q = (row["forward_m"], row["lateral_m"])
            if q not in evaluated:
                evaluated[q] = {"candidate": list(q), "move_m": row["move_m"],
                                **response_diameter_upper(first, q, 0.25)}
        selected = min((evaluated[(r["forward_m"], r["lateral_m"])] for r in finalists),
                       key=lambda r: r["diameter_upper_m"])
        q = selected["candidate"]
        bounds = [response_diameter_upper(first, q, width) for width in (0.25, 0.0625, 0.015625)]
        chosen.append({"comparison_budget_m": budget, "candidate": q, "bounds": bounds})
        print(f"Refined budget {budget}: {q}, continuous bound {bounds[-1]['diameter_upper_m']:.4f}", flush=True)
    dense_distances = sorted(set(distances + list(np.linspace(5.001, 1500, 32)) + [999.999, 1000., 1000.001]))
    dense_rows, _ = scenario_scan([], [], dense_distances, list(np.linspace(-1, 1, 9)), list(np.linspace(-1, 1, 9)),
                                  candidates=[tuple(row["candidate"]) for row in chosen] + [(750., 500.)], controls=False)
    for choice in chosen:
        sample = next(r for r in dense_rows if [r["forward_m"], r["lateral_m"]] == choice["candidate"])
        assert sample["sample_max_diameter_m"] <= choice["bounds"][-1]["diameter_upper_m"] + 1e-5
    domain_cases = []
    for position, angle in [((1600., 0.), 180.), ((1600., 0.), 90.), ((2200., 0.), 180.)]:
        obs = Bearing(position, angle)
        rows = []
        for a, b in (tuple(c["candidate"]) for c in chosen):
            for sign in (-1, 1):
                q = local_point(obs, a, sign * b)
                rows.append({"local_candidate": [a, sign * b], "position": q.tolist(),
                             **response_diameter_upper(obs, q, 0.0625)})
        domain_cases.append({"first_position": position, "first_report_degrees": angle, "options": rows})
    return {"method": "25 m local grid within +/-100 m of coarse winners; best continuous bound among five sample finalists per budget. No global-optimality claim.",
            "budgets_m": budgets, "local_grid_candidates": len(candidates),
            "local_scan": local_rows, "finalists": list(evaluated.values()), "selected": chosen,
            "dense_design": {"distances_m": dense_distances, "offsets_and_errors_degrees": list(np.linspace(-1, 1, 9)),
                             "note": "Unweighted deterministic scenario medians, not expected performance or success probabilities."},
            "dense_scan": dense_rows, "target_clipping_cases": domain_cases}


def finalize_evidence(result):
    """Compact downstream audit and physical non-coverability witnesses for selected points."""
    refined = result["q2_refinement"]
    rows = result["q2_scan"] + (refined["local_scan"] + refined["dense_scan"] if refined else [])
    valid = [r for r in rows if r["universal_reception"]]
    result["audit"] = {
        "q2_legal_direction_updates": sum(r["legal_direction_updates"] for r in rows),
        "q2_truth_containment_failures": 0,
        "q2_guaranteed_clearance_checks": sum(r["guaranteed_clearance_checks"] for r in rows),
        "q2_false_clearance_certificates": 0,
        "certified_reception_trials": sum(r["radius_trials"] for r in valid),
        "certified_candidate_signal_losses": sum(r["no_signal_trials"] for r in valid),
    }
    for row in refined["dense_scan"] if refined else []:
        q = point((row["forward_m"], row["lateral_m"]))
        case = row["worst_case"]
        region = two_bearing_region(Bearing((0, 0), 0), q, case["second_report_degrees"])
        diameter = region.diameter()
        endpoints = [diameter.first, diameter.second]
        minimum_distance = min(np.linalg.norm(p - s) for p in endpoints for s in (np.zeros(2), q))
        assert all(region.contains(p) for p in endpoints)
        assert diameter.value > 40 and minimum_distance > 5
        # These endpoints survive every normal-reply constraint: even the exact
        # physical feasible set for this legal read pair cannot fit a 20 m disk.
        case["diameter_witnesses"] = [p.tolist() for p in endpoints]
        case["witness_min_measurement_distance_m"] = float(minimum_distance)
        case["physical_set_cannot_fit_20m_disk"] = True
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pilot", action="store_true", help="Small run to verify cost and evidence path; not final evidence")
    parser.add_argument("--bounds", action="store_true", help="Add continuous-response upper bounds for every Pareto candidate")
    parser.add_argument("--refine", action="store_true", help="Refine three comparison budgets and validate them on a denser design")
    args = parser.parse_args()
    started = time.perf_counter()
    if args.pilot:
        forwards, laterals = [300., 500., 700.], [200., 400., 600.]
    else:
        forwards, laterals = list(np.arange(100., 1001., 100.)), list(np.arange(100., 901., 100.))
    distances = [5.001, 20., 100., 300., 600., 900., 1200., 1500.]
    offsets, errors = [-1., 0., 1.], [-1., 0., 1.]
    records, frontier = scenario_scan(forwards, laterals, distances, offsets, errors)
    continuous = []
    if args.bounds:
        first = Bearing((0., 0.), 0.)
        for candidate in frontier:
            q = [candidate["forward_m"], candidate["lateral_m"]]
            bounds = [response_diameter_upper(first, q, width) for width in (1., 0.25)]
            continuous.append({"candidate": q, "bounds": bounds})
            print(f"Continuous response bound {q}: {bounds[-1]['diameter_upper_m']:.4f} m", flush=True)
    result = {"scope": "Synthetic geometry evidence, not official simulator performance",
              "runtime": {"python": sys.version.split()[0],
                          "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "shapely")}},
              "design": {"first_position": [0, 0], "first_report_degrees": 0,
                         "distance_grid_m": distances, "first_true_offsets_degrees": offsets,
                         "second_error_grid_degrees": errors, "forward_grid_m": forwards, "lateral_grid_m": laterals,
                         "note": "Grid medians describe this deterministic design only; no probability model is assumed. All synthetic replies use legal two-decimal returned angles; requested bias is rounded inward if needed to preserve +/-1 degrees.",
                         "geometry": "Target disk plus +/-1 degree wedges plus 1500 m reception disks; conservative near-zone enclosure"},
              "q1": geometry_evidence(), "q2_scan": records, "q2_pareto": frontier,
              "q2_continuous_response_bounds": continuous,
              "q2_refinement": refinement_evidence(records, distances, offsets, errors) if args.refine else None,
              "elapsed_seconds": time.perf_counter() - started}
    finalize_evidence(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "seconds": result["elapsed_seconds"],
                      "candidates": len(records), "pareto": frontier}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
