"""Q1 geometry: intersections of closed halfplanes and disks, without polygonizing arcs.

Angles are degrees east-counterclockwise; coordinates/radii/tolerances are metres.
The mathematical algorithms are exact over real arithmetic. This implementation is
float64, with explicit metre tolerances, not an interval-arithmetic proof engine.
"""
from dataclasses import dataclass
from functools import cached_property
from itertools import combinations
import math

import numpy as np
from scipy.optimize import linprog

TAU = 2 * math.pi
GEOM_TOL = 2e-7
NUMERIC_GUARD = 2e-6


def point(value):
    p = np.asarray(value, dtype=float)
    if p.shape != (2,) or not np.isfinite(p).all():
        raise ValueError("Expected two finite coordinates")
    return p


def unit(angle):
    a = math.radians(float(angle) % 360)
    u = np.array([math.cos(a), math.sin(a)])
    u[np.abs(u) < 4 * np.finfo(float).eps] = 0
    return u


def cross(a, b):
    return float(a[0] * b[1] - a[1] * b[0])


@dataclass(frozen=True)
class Bearing:
    position: tuple[float, float]
    degrees: float
    error_degrees: float = 1.0

    def __post_init__(self):
        object.__setattr__(self, "position", tuple(point(self.position)))
        if not math.isfinite(self.degrees) or not 0 < self.error_degrees < 90:
            raise ValueError("Finite bearing and halfwidth strictly between 0 and 90 required")

    def halfplanes(self):
        lo, hi = unit(self.degrees - self.error_degrees), unit(self.degrees + self.error_degrees)
        # Inside is A x <= b; these two constraints select the FORWARD wedge.
        a = np.array([[lo[1], -lo[0]], [-hi[1], hi[0]]])
        return a, a @ point(self.position)


@dataclass(frozen=True)
class Disk:
    center: tuple[float, float]
    radius: float

    def __post_init__(self):
        object.__setattr__(self, "center", tuple(point(self.center)))
        if not math.isfinite(self.radius) or self.radius < 0:
            raise ValueError("Finite nonnegative radius required")


@dataclass(frozen=True)
class Arc:
    disk: int
    start: float
    end: float  # unwrapped, end > start, span <= 2 pi


@dataclass
class Diameter:
    value: float
    first: np.ndarray | None
    second: np.ndarray | None


@dataclass
class EnclosingCircle:
    center: np.ndarray
    radius_lower: float
    radius_upper: float
    iterations: int

    def clearance(self, radius=20.0):
        if self.radius_upper <= radius:
            return "guaranteed"
        if self.radius_lower > radius:
            return "not_coverable"
        return "numerical_boundary"


def _unique(points, tol=GEOM_TOL):
    out = []
    for p in points:
        if not any(np.linalg.norm(p - q) <= tol for q in out):
            out.append(np.asarray(p))
    return np.array(out, dtype=float).reshape((-1, 2))


def _line_circle(a, b, disk):
    c, r = point(disk.center), disk.radius
    signed = float(b - a @ c)
    if abs(signed) > r + GEOM_TOL:
        return []
    base = c + signed * a
    offset = math.sqrt(max(0.0, (r - abs(signed)) * (r + abs(signed))))
    t = np.array([-a[1], a[0]])
    return [base + offset * t, base - offset * t]


def _circle_circle(first, second):
    c, d = point(first.center), point(second.center)
    r, s = first.radius, second.radius
    length = float(np.linalg.norm(d - c))
    if length <= GEOM_TOL or length > r + s + GEOM_TOL or length < abs(r - s) - GEOM_TOL:
        return []
    u = (d - c) / length
    along = (length * length + (r - s) * (r + s)) / (2 * length)
    height = math.sqrt(max(0.0, (r - abs(along)) * (r + abs(along))))
    t = np.array([-u[1], u[0]])
    return [c + along * u + height * t, c + along * u - height * t]


class Region:
    """Closed convex intersection. Empty/unbounded are explicit, never boxed away.

    Disk boundaries remain circular arcs. `dimension` is numerical at GEOM_TOL;
    all constraints and boundary points remain stored for metric computations.
    """

    def __init__(self, a=(), b=(), disks=()):
        a = np.asarray(a, dtype=float).reshape((-1, 2))
        b = np.asarray(b, dtype=float).reshape(-1)
        if len(a) != len(b) or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError("Invalid halfplanes")
        norms = np.linalg.norm(a, axis=1)
        if np.any(norms == 0):
            raise ValueError("Zero halfplane normal")
        self.a, self.b = a / norms[:, None], b / norms
        # Exact duplicate normalized lines/circles, not near-parallel replacements.
        if len(a):
            _, keep = np.unique(np.column_stack((self.a, self.b)), axis=0, return_index=True)
            self.a, self.b = self.a[np.sort(keep)], self.b[np.sort(keep)]
        self.disks = list(dict.fromkeys(disks))

    def intersect(self, other):
        return Region(np.vstack((self.a, other.a)), np.r_[self.b, other.b], self.disks + other.disks)

    def contains(self, p, tol=GEOM_TOL):
        p = point(p)
        return bool(np.all(self.a @ p <= self.b + tol) and all(
            np.linalg.norm(p - point(d.center)) <= d.radius + tol for d in self.disks))

    @cached_property
    def _linear_status(self):
        if self.disks:
            return "bounded"
        if not len(self.a):
            return "unbounded"
        options = {"primal_feasibility_tolerance": 1e-9, "dual_feasibility_tolerance": 1e-9}
        # Establish feasibility before interpreting an unbounded objective.
        for objective in ([0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]):
            fit = linprog(objective, A_ub=self.a, b_ub=self.b,
                          bounds=[(None, None)] * 2, method="highs", options=options)
            if fit.status == 2:
                return "empty"
            if fit.status == 3:
                return "unbounded"
            if not fit.success:
                raise ArithmeticError(f"Halfplane feasibility unresolved: {fit.message}")
        return "bounded"

    @cached_property
    def _boundary(self):
        candidates, angles = [], [[] for _ in self.disks]
        for i, j in combinations(range(len(self.a)), 2):
            det = cross(self.a[i], self.a[j])
            if abs(det) > 1e-14:
                candidates.append(np.linalg.solve(self.a[[i, j]], self.b[[i, j]]))
        for k, disk in enumerate(self.disks):
            if disk.radius == 0:
                candidates.append(point(disk.center))
            for a, b in zip(self.a, self.b):
                for p in _line_circle(a, b, disk):
                    candidates.append(p)
                    angles[k].append(math.atan2(*(p - point(disk.center))[::-1]) % TAU)
        for i, j in combinations(range(len(self.disks)), 2):
            for p in _circle_circle(self.disks[i], self.disks[j]):
                candidates.append(p)
                for k in (i, j):
                    angles[k].append(math.atan2(*(p - point(self.disks[k].center))[::-1]) % TAU)
        vertices = _unique([p for p in candidates if self.contains(p)])
        arcs, midpoints = [], []
        for k, disk in enumerate(self.disks):
            if disk.radius == 0:
                continue
            breaks = sorted(set(angles[k])) or [0.0]
            for start, end in zip(breaks, breaks[1:] + [breaks[0] + TAU]):
                if end - start <= 1e-13:
                    continue
                middle = (start + end) / 2
                p = point(disk.center) + disk.radius * np.array([math.cos(middle), math.sin(middle)])
                if self.contains(p, tol=1e-9):
                    arcs.append(Arc(k, start, end))
                    midpoints.append(p)
        return vertices, arcs, _unique(midpoints)

    @property
    def vertices(self):
        return self._boundary[0]

    @property
    def arcs(self):
        return self._boundary[1]

    @cached_property
    def status(self):
        if self._linear_status != "bounded":
            return self._linear_status
        return "bounded" if len(self.vertices) or self.arcs else "empty"

    @cached_property
    def dimension(self):
        if self.status != "bounded":
            return None
        if self.arcs:
            return 2
        delta = self.vertices - self.vertices[0]
        return int(np.linalg.matrix_rank(delta, tol=GEOM_TOL))

    def _require_bounded(self):
        if self.status != "bounded":
            raise ValueError(f"Metric requires nonempty bounded region, got {self.status}")

    def farthest(self, center):
        """Analytic farthest point: vertices and the opposite radial point on each arc."""
        self._require_bounded()
        center = point(center)
        candidates = list(self.vertices) + list(self._boundary[2])
        for k in {arc.disk for arc in self.arcs}:
            disk = self.disks[k]
            delta = point(disk.center) - center
            length = np.linalg.norm(delta)
            if length > GEOM_TOL:
                p = point(disk.center) + disk.radius * delta / length
                if self.contains(p):
                    candidates.append(p)
        values = [np.linalg.norm(p - center) for p in candidates]
        i = int(np.argmax(values))
        return float(values[i]), np.asarray(candidates[i])

    def support(self, direction):
        self._require_bounded()
        direction = point(direction)
        length = np.linalg.norm(direction)
        if length == 0:
            raise ValueError("Zero support direction")
        candidates = list(self.vertices) + list(self._boundary[2])
        for k in {arc.disk for arc in self.arcs}:
            disk = self.disks[k]
            p = point(disk.center) + disk.radius * direction / length
            if self.contains(p):
                candidates.append(p)
        values = [float(direction @ p) for p in candidates]
        i = int(np.argmax(values))
        return values[i], np.asarray(candidates[i])

    def diameter(self):
        if self.status == "empty":
            return Diameter(math.nan, None, None)
        if self.status == "unbounded":
            return Diameter(math.inf, None, None)
        seeds = list(self.vertices) + list(self._boundary[2])
        best = Diameter(0.0, seeds[0], seeds[0])

        def consider(p, q):
            nonlocal best
            value = float(np.linalg.norm(p - q))
            if value > best.value:
                best = Diameter(value, p, q)

        for p in seeds:
            _, q = self.farthest(p)
            consider(p, q)
        active = sorted({arc.disk for arc in self.arcs})
        # Two interior arc points must be collinear with the two circle centers.
        for i, j in combinations(active, 2):
            d, e = self.disks[i], self.disks[j]
            delta = point(e.center) - point(d.center)
            length = np.linalg.norm(delta)
            if length <= GEOM_TOL:
                continue
            u = delta / length
            for sign in (-1, 1):
                for other in (-1, 1):
                    p, q = point(d.center) + sign * d.radius * u, point(e.center) + other * e.radius * u
                    if self.contains(p) and self.contains(q):
                        consider(p, q)
        # Antipodal points on one circle: arc endpoints and their pi shifts partition angles.
        for k in active:
            disk = self.disks[k]
            breaks = sorted({a % TAU for arc in self.arcs if arc.disk == k
                             for a in (arc.start, arc.end, arc.start + math.pi, arc.end + math.pi)})
            probe = breaks + [(a + b) / 2 for a, b in zip(breaks, breaks[1:] + [breaks[0] + TAU])]
            for angle in probe:
                offset = disk.radius * np.array([math.cos(angle), math.sin(angle)])
                p, q = point(disk.center) + offset, point(disk.center) - offset
                if self.contains(p) and self.contains(q):
                    consider(p, q)
                    break
        return best

    def area(self):
        self._require_bounded()
        if self.dimension < 2:
            return 0.0
        # Translate the Green-integral origin to reduce cancellation for tiny regions.
        origin = np.mean(np.vstack((self.vertices, self._boundary[2])), axis=0)
        total = 0.0
        for a, b in zip(self.a, self.b):
            boundary = self.vertices[np.abs(self.vertices @ a - b) <= GEOM_TOL]
            if len(boundary) >= 2:
                t = np.array([-a[1], a[0]])
                ranks = boundary @ t
                total += cross(boundary[np.argmin(ranks)] - origin, boundary[np.argmax(ranks)] - origin)
        for arc in self.arcs:
            disk = self.disks[arc.disk]
            c, r = point(disk.center) - origin, disk.radius
            a, b = arc.start, arc.end
            total += r * r * (b - a) + r * c[0] * (math.sin(b) - math.sin(a)) + r * c[1] * (math.cos(a) - math.cos(b))
        return max(0.0, total / 2)

    def enclosing_circle(self, tolerance=1e-4, max_iterations=100):
        """Exchange algorithm; finite-set lower bound versus analytic farthest upper bound."""
        self._require_bounded()
        if tolerance <= 2 * NUMERIC_GUARD:
            raise ValueError("Requested tolerance must exceed float64 safety guard")
        diameter = self.diameter()
        witnesses = _unique([*self.vertices, *self._boundary[2], diameter.first, diameter.second])
        for iteration in range(1, max_iterations + 1):
            center, lower = minimum_circle_of_points(witnesses)
            upper, farthest = self.farthest(center)
            if upper - lower <= tolerance - 2 * NUMERIC_GUARD:
                return EnclosingCircle(center, max(0.0, lower - NUMERIC_GUARD),
                                       upper + NUMERIC_GUARD, iteration)
            witnesses = np.vstack((witnesses, farthest))
        raise ArithmeticError("Enclosing-circle exchange did not reach its requested gap")


def _three_circle(p, q, r):
    u, v = q - p, r - p
    det = cross(u, v)
    if abs(det) <= 1e-14 * max(np.linalg.norm(u) * np.linalg.norm(v), 1.0):
        pairs = [(a, b) for a, b in combinations((p, q, r), 2)]
        a, b = max(pairs, key=lambda pair: np.linalg.norm(pair[0] - pair[1]))
        return (a + b) / 2, float(np.linalg.norm(a - b) / 2)
    center = p + np.linalg.solve(2 * np.array([u, v]), np.array([u @ u, v @ v]))
    return center, float(np.linalg.norm(center - p))


def minimum_circle_of_points(points):
    """Randomized-order incremental 1/2/3-support circle; seed fixes algorithm order only."""
    points = np.asarray(points, dtype=float).reshape((-1, 2))
    if not len(points):
        raise ValueError("Empty point set")
    points = points[np.random.default_rng(0).permutation(len(points))]
    center, radius = points[0].copy(), 0.0
    for i, p in enumerate(points):
        if np.linalg.norm(p - center) <= radius + 1e-10:
            continue
        center, radius = p.copy(), 0.0
        for j, q in enumerate(points[:i]):
            if np.linalg.norm(q - center) <= radius + 1e-10:
                continue
            center, radius = (p + q) / 2, float(np.linalg.norm(p - q) / 2)
            for r in points[:j]:
                if np.linalg.norm(r - center) > radius + 1e-10:
                    center, radius = _three_circle(p, q, r)
    # This is only a rounding correction; geometric errors are caught by independent tests.
    return center, float(max(np.linalg.norm(points - center, axis=1)))


def localization_region(observations, *, target=Disk((0.0, 0.0), 1800.0), reception_bound=None):
    """Exact intersection for bearing wedges plus the declared disks.

    With reception_bound=1500 this is a conservative closed position enclosure
    for normal replies: it deliberately does not cut out the open 5 m near-zone.
    That exclusion must not be confused with changing the official error bound.
    Set target=None to obtain the pure (possibly unbounded) Q1 polygon.
    """
    a, b, disks = [], [], [] if target is None else [target]
    for observation in observations:
        rows, bounds = observation.halfplanes()
        a.extend(rows)
        b.extend(bounds)
        if reception_bound is not None:
            disks.append(Disk(tuple(observation.position), reception_bound))
    return Region(a, b, disks)
