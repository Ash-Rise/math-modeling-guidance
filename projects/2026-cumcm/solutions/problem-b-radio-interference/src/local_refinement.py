"""Certified follow-up probes after two or more omnidirectional bearings."""
from __future__ import annotations

import math

import numpy as np

from radio_geometry import Bearing, Disk, GEOM_TOL, Region, point
from second_point import pareto_indices


def bearing_update(prior: Region, location, degrees: float, error_degrees: float = 1.0) -> Region:
    """Intersect a current enclosure with one normal direction reply."""
    q = point(location)
    rows, bounds = Bearing(tuple(q), degrees, error_degrees).halfplanes()
    return prior.intersect(Region(rows, bounds, [Disk(tuple(q), 1500.0)]))


def guaranteed_reception_margin(prior: Region, location) -> float:
    """Positive iff every point in the current enclosure is within the 1000 m minimum range."""
    distance, _ = prior.farthest(location)
    return 1000.0 - distance


def response_radius_upper(prior: Region, location, bin_degrees: float = 5.0) -> dict:
    """Upper-bound the next posterior enclosing radius for every possible direction reply.

    Every returned angle lies in one bin. Enlarging its +/-1 degree wedge by half
    the bin width encloses the posterior for every reply in that bin. Scanning a
    full turn is conservative when the candidate lies inside the prior region.
    """
    if not 0 < bin_degrees <= 10:
        raise ValueError("Use a positive direction-bin width no larger than 10 degrees")
    margin = guaranteed_reception_margin(prior, location)
    if margin < -GEOM_TOL:
        raise ValueError("Candidate does not guarantee reception for the current enclosure")
    edges = np.linspace(0.0, 360.0, math.ceil(360.0 / bin_degrees) + 1)
    worst_radius, worst_angle, nonempty = 0.0, None, 0
    for left, right in zip(edges[:-1], edges[1:]):
        middle = (left + right) / 2
        posterior = bearing_update(prior, location, middle, 1.0 + (right - left) / 2)
        if posterior.status == "empty":
            continue
        nonempty += 1
        circle = posterior.enclosing_circle()
        if circle.radius_upper > worst_radius:
            worst_radius = circle.radius_upper
            worst_angle = middle
    if not nonempty:
        raise ArithmeticError("No direction bin intersects a nonempty prior enclosure")
    return {
        "bin_degrees": float(np.max(np.diff(edges))),
        "radius_upper_m": float(worst_radius),
        "worst_bin_center_degrees": float(worst_angle),
        "nonempty_bins": nonempty,
        "reception_margin_m": float(margin),
    }


def local_probe_options(
    prior: Region,
    current,
    *,
    radii=(150.0, 300.0, 500.0, 700.0),
    directions: int = 16,
    move_budget: float | None = 700.0,
    bin_degrees: float = 5.0,
) -> dict:
    """Compare finite guaranteed-reception probes around the current minimum circle.

    The optional movement budget is explicit. Selection minimizes the certified
    radius over the supplied finite design; without a budget only the Pareto set
    is returned and no unique optimum is asserted.
    """
    if directions < 4:
        raise ValueError("At least four directions are required")
    if move_budget is not None and (not math.isfinite(move_budget) or move_budget <= 0):
        raise ValueError("Movement budget must be positive and finite")
    current = point(current)
    circle = prior.enclosing_circle()
    rows = []
    for radius in radii:
        if not math.isfinite(radius) or radius <= 0:
            raise ValueError("Candidate radii must be positive and finite")
        for k in range(directions):
            angle = 360.0 * k / directions
            q = circle.center + radius * np.array([math.cos(math.radians(angle)), math.sin(math.radians(angle))])
            move = float(np.linalg.norm(q - current))
            if move <= GEOM_TOL or (move_budget is not None and move > move_budget + GEOM_TOL):
                continue
            margin = guaranteed_reception_margin(prior, q)
            if margin < -GEOM_TOL:
                continue
            bound = response_radius_upper(prior, q, bin_degrees)
            rows.append({
                "position": q.tolist(),
                "angle_degrees": angle,
                "offset_from_enclosing_center_m": float(radius),
                "move_m": move,
                "move_and_measure_s": move / 5.0 + 5.0,
                **bound,
            })
    front = [rows[i] for i in pareto_indices(rows, ("move_m", "radius_upper_m"))] if rows else []
    front.sort(key=lambda row: row["move_m"])
    best = min(front, key=lambda row: (row["radius_upper_m"], row["move_m"])) if front and move_budget is not None else None
    return {
        "prior_radius_upper_m": float(circle.radius_upper),
        "evaluated_candidates": len(rows),
        "pareto": front,
        "best_with_supplied_budget": best,
    }
