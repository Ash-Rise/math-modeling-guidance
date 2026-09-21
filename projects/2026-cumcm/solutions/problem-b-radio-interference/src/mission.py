"""End-to-end Q3/Q4 search, localization and clear policies."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import time

import numpy as np

from local_refinement import bearing_update, local_probe_options
from radio_geometry import Bearing, point
from search_strategy import fallback_clear_points, q3_search_points, q4_search_points
from second_point import local_point, two_bearing_region


@dataclass
class MissionResult:
    mode: str
    cleared_channels: list[int]
    virtual_time_s: float
    program_runtime_s: float
    measure_requests: int
    clear_requests: int
    failed_clears: int
    certified_circle_clears: int
    fallback_channels: int
    search_points_completed: int

    def to_dict(self) -> dict:
        return asdict(self)


def _clear_fallback(backend, first: Bearing, channel: int) -> tuple[bool, int]:
    attempts = 0
    for candidate in fallback_clear_points(first):
        attempts += 1
        if backend.clear(candidate, channel)["result"] == "success":
            return True, attempts
    return False, attempts


def _second_location(first: Bearing) -> np.ndarray:
    choices = [local_point(first, 550.0, lateral) for lateral in (-575.0, 575.0)]
    # Target clipping makes the side closer to the origin weakly preferable and
    # preserves the proved universal-reception construction.
    return min(choices, key=lambda candidate: float(np.linalg.norm(candidate)))


def _service_omnidirectional(backend, channel: int, first: Bearing,
                             first_result: dict, *, max_refinements: int = 3) -> tuple[bool, bool]:
    if first_result["result"] == "near":
        return backend.clear(first.position, channel)["result"] == "success", True
    second = _second_location(first)
    reply = backend.measure(second, channel)
    if reply["result"] == "near":
        return backend.clear(second, channel)["result"] == "success", True
    if reply["result"] != "direction":
        raise RuntimeError("Proved omnidirectional second point unexpectedly lost signal")
    prior = two_bearing_region(first, second, reply["degrees"])
    current = second
    for _ in range(max_refinements + 1):
        circle = prior.enclosing_circle()
        if circle.radius_upper <= 20.0:
            if backend.clear(circle.center, channel)["result"] == "success":
                return True, True
            break
        options = local_probe_options(prior, current, radii=(150.0, 300.0, 500.0),
                                      directions=8, move_budget=700.0, bin_degrees=10.0)
        chosen = options["best_with_supplied_budget"]
        if chosen is None:
            break
        current = point(chosen["position"])
        reply = backend.measure(current, channel)
        if reply["result"] == "near":
            return backend.clear(current, channel)["result"] == "success", True
        if reply["result"] != "direction":
            raise RuntimeError("Guaranteed-reception refinement unexpectedly lost signal")
        prior = bearing_update(prior, current, reply["degrees"])
    success, _ = _clear_fallback(backend, first, channel)
    return success, False


def run_mission(backend, mode: str) -> MissionResult:
    """Run a complete policy without reading the hidden source count.

    The backend must implement synchronous ``measure`` and ``clear`` and expose
    virtual-time/request counters. Q3 uses geometry-first localization; Q4 uses
    the direction-independent optical fallback after the first positive reply.
    """
    if mode not in {"q3", "q4"}:
        raise ValueError("mode must be q3 or q4")
    started = time.perf_counter()
    search_points = q3_search_points() if mode == "q3" else q4_search_points()
    unresolved = set(range(1, 21))
    cleared = []
    certified, fallback = 0, 0
    completed = 0
    for location in search_points:
        hits = []
        for channel in sorted(unresolved):
            reply = backend.measure(location, channel)
            if reply["result"] != "no_signal":
                hits.append((channel, reply))
        completed += 1
        for channel, reply in hits:
            if channel not in unresolved:
                continue
            first = Bearing(tuple(point(location)), reply.get("degrees", 0.0))
            if mode == "q3":
                success, used_certificate = _service_omnidirectional(
                    backend, channel, first, reply)
                certified += int(used_certificate and success)
                fallback += int(not used_certificate)
            else:
                if reply["result"] == "near":
                    success = backend.clear(location, channel)["result"] == "success"
                    certified += int(success)
                else:
                    success, _ = _clear_fallback(backend, first, channel)
                    fallback += 1
            if not success:
                raise RuntimeError(f"Fallback construction failed for channel {channel}")
            unresolved.remove(channel)
            cleared.append(channel)
        if len(cleared) == 16:
            break
    return MissionResult(
        mode=mode,
        cleared_channels=sorted(cleared),
        virtual_time_s=float(backend.virtual_time_s),
        program_runtime_s=time.perf_counter() - started,
        measure_requests=int(backend.measure_requests),
        clear_requests=int(backend.clear_requests),
        failed_clears=int(backend.failed_clears),
        certified_circle_clears=certified,
        fallback_channels=fallback,
        search_points_completed=completed,
    )
