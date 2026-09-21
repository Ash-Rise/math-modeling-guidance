"""Distribution-free Q2 candidates and response-cell upper bounds using Q1 geometry."""
import math

import numpy as np

from radio_geometry import Bearing, Disk, GEOM_TOL, NUMERIC_GUARD, Region, localization_region, point, unit


def local_point(first, forward, lateral):
    u = unit(first.degrees)
    v = np.array([-u[1], u[0]])
    return point(first.position) + forward * u + lateral * v


def guaranteed_candidate_region(first):
    """Four-disk representation for the full 5 < rho <= 1500 first-bearing sector.

    R is unknown in [1000,1500], but the first reception implies R >= rho.
    Exact for the full sector; a sufficient, possibly conservative subset after
    the target disk clips that sector. The 5 m limiting endpoint is included to
    give a closed robust candidate set, without asserting a normal reply at 5 m.
    """
    centers = [point(first.position) + radius * unit(first.degrees + sign * first.error_degrees)
               for radius in (5.0, 1000.0) for sign in (-1, 1)]
    return Region(disks=[Disk(tuple(c), 1000.0) for c in centers])


def reception_margin(first, q):
    """Minimum four-disk slack, metres; nonnegative certifies universal reception."""
    q = point(q)
    return min(d.radius - np.linalg.norm(q - point(d.center))
               for d in guaranteed_candidate_region(first).disks)


def two_bearing_region(first, q, second_degrees, second_error=1.0):
    return localization_region([first, Bearing(tuple(q), second_degrees, second_error)], reception_bound=1500.0)


def synthetic_reply(source, radius, location, bias_degrees):
    """Known-truth *test* observation, not an emulator of the hidden generator.

    Caller must reuse the same bias on repeated locations. Choose a two-decimal
    returned angle within the official +/-1 interval; rounding must never push
    an endpoint error outside that interval. Requested and realized bias can
    differ by less than 0.01 degrees. This does not model hidden rounding order.
    """
    source, location = point(source), point(location)
    if not 1000 <= radius <= 1500 or not -1 <= bias_degrees <= 1:
        raise ValueError("Scenario outside official bounds")
    distance = float(np.linalg.norm(source - location))
    # Floating coordinates on the exact reception boundary may be a few ulps
    # outside it. This metre tolerance is numerical, not a sensor error model.
    if distance > radius + GEOM_TOL:
        return {"result": "no_signal"}
    if distance <= 5 + GEOM_TOL:
        return {"result": "near"}
    delta = source - location
    angle = math.degrees(math.atan2(delta[1], delta[0]))
    low = math.ceil(100 * (angle - 1) - 1e-10)
    high = math.floor(100 * (angle + 1) + 1e-10)
    ticks = min(high, max(low, round(100 * (angle + bias_degrees))))
    return {"result": "direction", "degrees": (ticks % 36000) / 100}


def response_diameter_upper(first, q, bin_degrees=0.5):
    """Cover ALL possible second angles by finite bins, with rigorous geometric enlargement.

    Each bin midpoint uses halfwidth 1 + bin_width/2, so it contains the posterior
    of every actual reported angle in that bin. This is a computational enclosure,
    not an altered sensor error model. The output upper-bounds every posterior
    diameter of the closed convex Q1 enclosure; normal-reply 5 m holes are omitted.
    Candidates inside the conservative first-sector rectangle use a full turn.
    """
    q = point(q)
    if not 0 < bin_degrees <= 2:
        raise ValueError("Use a positive angle-bin width <= 2 degrees")
    if reception_margin(first, q) < -GEOM_TOL:
        raise ValueError("Candidate has no universal reception certificate")
    u = unit(first.degrees)
    v = np.array([-u[1], u[0]])
    delta = q - point(first.position)
    a, b = float(delta @ u), float(delta @ v)
    height = 1500 * math.sin(math.radians(first.error_degrees))
    reference = math.atan2(-b, 750 - a)
    corners = [(x, y) for x in (0.0, 1500.0) for y in (-height, height)]
    angles = [reference + (math.atan2(y - b, x - a) - reference + math.pi) % (2 * math.pi) - math.pi
              for x, y in corners]
    if 0 <= a <= 1500 and abs(b) <= height:
        low, high = 0.0, 360.0
    else:
        low = math.degrees(min(angles)) + first.degrees - 1
        high = math.degrees(max(angles)) + first.degrees + 1
    edges = np.linspace(low, high, math.ceil((high - low) / bin_degrees) + 1)
    maximum, witness_angle, nonempty = 0.0, None, 0
    for left, right in zip(edges[:-1], edges[1:]):
        middle = (left + right) / 2
        region = two_bearing_region(first, q, middle, 1.0 + (right - left) / 2)
        if region.status == "empty":
            continue
        nonempty += 1
        value = region.diameter().value
        if value > maximum:
            maximum, witness_angle = value, middle
    return {"bin_degrees": float(np.max(np.diff(edges))),
            "diameter_upper_m": maximum + NUMERIC_GUARD,
            "worst_bin_center_degrees": witness_angle,
            "bins": len(edges) - 1, "nonempty_bins": nonempty}


def pareto_indices(records, fields=("move_m", "sample_max_diameter_m")):
    """Nondominance only. No weighting, prior, or unique optimum is implied."""
    values = np.array([[record[field] for field in fields] for record in records])
    return [i for i, row in enumerate(values)
            if not np.any(np.all(values <= row + 1e-8, axis=1) & np.any(values < row - 1e-8, axis=1))]


def second_point_options(first, local_candidates, *, bin_degrees=0.25, move_budget=None):
    """Certified reception and worst-response bounds for supplied finite candidates.

    Returns a Pareto set in movement and posterior diameter upper bound, with no
    implicit budget/weight or probability distribution. A supplied budget filters
    movement first. The recommendation then minimizes the bound over THIS set;
    it is not an assertion of a globally optimal point in the continuous domain.
    The target disk is used when evaluating each sign/position. Repeated sites
    are excluded: the official location-fixed error gives no new observation.
    """
    if move_budget is not None and (not math.isfinite(move_budget) or move_budget < 0):
        raise ValueError("Movement budget must be finite and nonnegative")
    if localization_region([first], reception_bound=1500).status == "empty":
        raise ValueError("First bearing is inconsistent with the target and reception domains")
    rows = []
    for a, b in dict.fromkeys(tuple(pair) for pair in local_candidates):
        q = local_point(first, a, b)
        move = math.hypot(a, b)
        margin = reception_margin(first, q)
        if move == 0 or margin < 0 or (move_budget is not None and move > move_budget):
            continue
        bound = response_diameter_upper(first, q, bin_degrees)
        rows.append({"forward_m": float(a), "lateral_m": float(b), "position": q.tolist(),
                     "move_m": move, "move_and_second_measure_s": move / 5 + 5,
                     "reception_margin_m": float(margin), **bound})
    front = [rows[i] for i in pareto_indices(rows, ("move_m", "diameter_upper_m"))] if rows else []
    front.sort(key=lambda r: r["move_m"])
    best = min(front, key=lambda r: (r["diameter_upper_m"], r["move_m"])) if front and move_budget is not None else None
    return {"pareto": front, "best_with_supplied_budget": best}
