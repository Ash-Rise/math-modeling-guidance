import itertools
import math

import numpy as np
import pytest
from scipy.optimize import minimize

from radio_geometry import Bearing, Disk, Region, localization_region, minimum_circle_of_points


def test_forward_wrap_and_inclusive_angle_bounds():
    obs = Bearing((0, 0), 359.5)
    region = localization_region([obs])
    for angle in (358.5, 359.5, 0.5):
        p = 1200 * np.array([math.cos(math.radians(angle)), math.sin(math.radians(angle))])
        assert region.contains(p)
    assert not region.contains((-100, 0))
    assert not region.contains((1900, 0))
    assert localization_region([obs], target=None).status == "unbounded"


def test_empty_point_segment_and_full_disk():
    disk = Disk((0, 0), 1)
    empty = Region([[-1, 0]], [-1.01], [disk])
    assert empty.status == "empty" and math.isnan(empty.diameter().value)
    with pytest.raises(ValueError):
        empty.enclosing_circle()
    tangent = Region([[-1, 0]], [-1], [disk])
    assert tangent.dimension == 0
    assert tangent.diameter().value == pytest.approx(0, abs=1e-6)
    segment = Region([[0, 1], [0, -1]], [0, 0], [disk])
    assert segment.dimension == 1
    assert segment.diameter().value == pytest.approx(2)
    assert segment.area() == 0
    full = Region(disks=[disk])
    assert full.dimension == 2
    assert full.diameter().value == pytest.approx(2)
    assert full.area() == pytest.approx(math.pi)
    assert full.enclosing_circle().radius_lower <= 1 <= full.enclosing_circle().radius_upper


def test_halfplane_empty_unbounded_and_zero_radius():
    assert Region([[1, 0], [-1, 0]], [0, -1]).status == "empty"
    assert Region([[0, 1], [0, -1]], [0, -1]).status == "empty"  # x itself is unrestricted
    assert Region([[1, 0]], [1]).diameter().value == math.inf
    assert Region(disks=[Disk((2, 3), 0)]).dimension == 0


def test_arc_interior_diameter_cannot_use_vertices_only():
    # A vertical strip in the unit disk. All four vertices have |y| < 1,
    # but the diameter is the antipodal pair (0, +/-1), inside circular arcs.
    strip = Region([[1, 0], [-1, 0]], [0.2, 0.2], [Disk((0, 0), 1)])
    vertex_diameter = max(np.linalg.norm(p - q) for p in strip.vertices for q in strip.vertices)
    assert vertex_diameter <= 2 + 1e-12  # diagonal vertices can also be antipodal
    cap = Region([[-1, 0]], [-0.5], [Disk((0, 0), 1)])
    assert cap.diameter().value == pytest.approx(math.sqrt(3))
    assert cap.area() == pytest.approx(math.pi / 3 - math.sqrt(3) / 4)
    # Asymmetric strip: no pair of vertices is antipodal, but arc interiors are.
    strip = Region([[1, 0], [-1, 0]], [0.1, 0.2], [Disk((0, 0), 1)])
    vertex_diameter = max(np.linalg.norm(p - q) for p in strip.vertices for q in strip.vertices)
    assert vertex_diameter < 2
    assert strip.diameter().value == pytest.approx(2)


def test_lens_circle_intersections_tangency_and_containment():
    lens = Region(disks=[Disk((-0.5, 0), 1), Disk((0.5, 0), 1)])
    assert lens.diameter().value == pytest.approx(math.sqrt(3))
    assert lens.area() == pytest.approx(2 * math.pi / 3 - math.sqrt(3) / 2)
    tangent = Region(disks=[Disk((0, 0), 1), Disk((2, 0), 1)])
    assert tangent.dimension == 0
    nested = Region(disks=[Disk((0, 0), 2), Disk((0.2, 0), 1)])
    assert nested.diameter().value == pytest.approx(2)
    assert nested.area() == pytest.approx(math.pi)


def test_realizable_equilateral_counterexample():
    vertices = np.array([[0., 0.], [40., 0.], [20., 20 * math.sqrt(3)]])
    observations = []
    for i in range(3):
        direction = (vertices[(i + 1) % 3] - vertices[i]) / 40
        s = vertices[i] - 1000 * direction
        observations.append(Bearing(tuple(s), math.degrees(math.atan2(direction[1], direction[0])) + 1))
    for target in (None, Disk((0, 0), 1800)):
        region = localization_region(observations, target=target)
        assert all(region.contains(v) for v in vertices)
        assert region.diameter().value == pytest.approx(40)
        circle = region.enclosing_circle()
        assert circle.radius_lower > 20
        assert circle.radius_lower <= 40 / math.sqrt(3) <= circle.radius_upper
        assert circle.clearance() == "not_coverable"


def test_repeated_observation_does_not_shrink_and_nearly_parallel_is_stable():
    obs = Bearing((0, 0), 0)
    first = localization_region([obs], reception_bound=1500)
    repeated = localization_region([obs, obs], reception_bound=1500)
    assert repeated.diameter().value == pytest.approx(first.diameter().value)
    assert repeated.area() == pytest.approx(first.area())
    g = np.array([1490., 0.])
    s = (1., 1e-3)
    other = Bearing(s, math.degrees(math.atan2(g[1] - s[1], g[0] - s[0])))
    region = localization_region([obs, other], reception_bound=1500)
    assert region.contains(g) and region.status == "bounded"
    assert region.diameter().value <= first.diameter().value + 1e-5


def test_clearance_boundary_and_safe_point():
    for radius, expected in ((19.9, "guaranteed"), (20., "numerical_boundary"), (20.1, "not_coverable")):
        region = Region(disks=[Disk((100, -200), radius)])
        circle = region.enclosing_circle()
        assert circle.clearance() == expected
        if expected == "guaranteed":
            assert region.farthest(circle.center)[0] <= 20


def test_point_circle_against_independent_all_support_enumeration():
    rng = np.random.default_rng(341)
    for _ in range(20):
        points = rng.normal(size=(8, 2))
        candidates = [(p, 0.) for p in points]
        for p, q in itertools.combinations(points, 2):
            c = (p + q) / 2
            candidates.append((c, np.linalg.norm(c - p)))
        for p, q, r in itertools.combinations(points, 3):
            matrix = 2 * np.array([q - p, r - p])
            if abs(np.linalg.det(matrix)) < 1e-12:
                continue
            c = np.linalg.solve(matrix, np.array([q @ q - p @ p, r @ r - p @ p]))
            candidates.append((c, np.linalg.norm(c - p)))
        best = min(radius for center, radius in candidates
                   if np.max(np.linalg.norm(points - center, axis=1)) <= radius + 1e-9)
        center, radius = minimum_circle_of_points(points)
        assert radius == pytest.approx(best, abs=1e-8)


def test_random_support_against_independent_convex_optimizer():
    rng = np.random.default_rng(771)
    for _ in range(12):
        truth = rng.uniform(-900, 900, 2)
        observations = []
        for _ in range(3):
            angle = rng.uniform(0, 2 * math.pi)
            s = truth - rng.uniform(100, 1400) * np.array([math.cos(angle), math.sin(angle)])
            observations.append(Bearing(tuple(s), math.degrees(angle) + rng.uniform(-1, 1)))
            region = localization_region(observations, reception_bound=1500)
            assert region.contains(truth)
        direction = rng.normal(size=2)
        value, witness = region.support(direction)
        constraints = [{"type": "ineq", "fun": lambda x: region.b - region.a @ x}]
        for d in region.disks:
            constraints.append({"type": "ineq", "fun": lambda x, d=d: d.radius - np.linalg.norm(x - d.center)})
        fit = minimize(lambda x: -direction @ x, truth, jac=lambda x: -direction,
                       constraints=constraints, method="SLSQP", options={"ftol": 1e-9, "maxiter": 200})
        assert fit.success, fit.message
        assert value == pytest.approx(float(direction @ fit.x), abs=2e-4)
        assert region.contains(witness, tol=1e-5)
        circle = region.enclosing_circle()
        assert np.linalg.norm(truth - circle.center) <= circle.radius_upper
        if circle.clearance() == "guaranteed":
            assert np.linalg.norm(truth - circle.center) <= 20
