"""Deterministic coverage and fallback-clear constructions for Q3/Q4."""
from __future__ import annotations

import math

import numpy as np

from radio_geometry import Bearing, point, unit


def q3_search_points() -> list[np.ndarray]:
    """Seven-point route whose 900 m disks cover the 1800 m target disk."""
    ring = 900.0 * math.sqrt(3.0)
    return [np.zeros(2)] + [ring * unit(angle) for angle in range(0, 360, 60)]


def _nearest_route(points, start=(0.0, 0.0)) -> list[np.ndarray]:
    remaining = [point(p) for p in points]
    current = point(start)
    route = []
    while remaining:
        index = min(range(len(remaining)), key=lambda i: (
            float(np.linalg.norm(remaining[i] - current)),
            float(remaining[i][0]), float(remaining[i][1])))
        current = remaining.pop(index)
        route.append(current)
    return route


def q4_search_points() -> list[np.ndarray]:
    """Nearest-neighbour route through the 69-point directional cover."""
    points = [np.array([600.0 * i, 600.0 * j])
              for i in range(-4, 5) for j in range(-4, 5)
              if 600.0 * math.hypot(i, j) <= 2800.0]
    assert len(points) == 69
    return _nearest_route(points)


def fallback_clear_points(first: Bearing) -> list[np.ndarray]:
    """304-point cover of the full first-bearing wedge enclosure.

    In first-bearing coordinates, every compatible source has
    0 <= x <= 1500 and |y| < 30. The 20 m square spacing gives covering
    radius sqrt(200) < 20 m. The snake order has a simple path bound.
    """
    origin = point(first.position)
    forward = unit(first.degrees)
    lateral = np.array([-forward[1], forward[0]])
    xs = np.arange(0.0, 1500.0 + 1e-9, 20.0)
    ys = (-30.0, -10.0, 10.0, 30.0)
    points = []
    for row, y in enumerate(ys):
        ordered = xs if row % 2 == 0 else xs[::-1]
        points.extend(origin + x * forward + y * lateral for x in ordered)
    assert len(points) == 304
    return points
