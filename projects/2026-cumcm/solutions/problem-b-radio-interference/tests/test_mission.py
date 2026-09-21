import math

import numpy as np

from mission import run_mission
from offline_simulator import OfflineArena, Source
from radio_geometry import Bearing, unit
from search_strategy import fallback_clear_points, q3_search_points, q4_search_points


def test_q3_and_q4_cover_constructions_on_dense_deterministic_designs():
    q3 = np.asarray(q3_search_points())
    assert q3.shape == (7, 2)
    for radius in np.linspace(0, 1800, 37):
        for angle in np.linspace(0, 360, 145)[:-1]:
            source = radius * unit(angle)
            assert np.min(np.linalg.norm(q3 - source, axis=1)) <= 900.0 + 1e-7

    q4 = np.asarray(q4_search_points())
    assert q4.shape == (69, 2)
    for radius in np.linspace(0, 1800, 13):
        for angle in np.linspace(0, 360, 49)[:-1]:
            source = radius * unit(angle)
            for direction in np.linspace(0, 360, 25)[:-1]:
                delta = q4 - source
                covered = ((np.linalg.norm(delta, axis=1) <= 1000.0 + 1e-8) &
                           (delta @ unit(direction) >= -1e-8))
                assert covered.any()


def test_fallback_grid_covers_every_sampled_first_bearing_wedge():
    first = Bearing((137.0, -251.0), 33.0)
    points = np.asarray(fallback_clear_points(first))
    assert len(points) == 304
    for distance in np.linspace(0, 1500, 151):
        for error in np.linspace(-1, 1, 9):
            truth = np.asarray(first.position) + distance * unit(first.degrees + error)
            assert np.min(np.linalg.norm(points - truth, axis=1)) < 20.0


def test_offline_arena_reproduces_official_199_second_timing_example():
    sources = [Source(channel=i, position=(-1700 + 10 * i, 0), radius=1000)
               for i in range(1, 11)]
    arena = OfflineArena(sources)
    arena.measure((300, 400), 1)
    assert arena.virtual_time_s == 105
    arena.measure((300, 400), 2)
    assert arena.virtual_time_s == 111
    assert arena.clear((300, 0), 3)["result"] == "no_target_in_range"
    assert arena.virtual_time_s == 194
    arena.measure((300, 0), 2)
    assert arena.virtual_time_s == 199


def _near_sources(points, *, directional=False):
    points = list(points)
    return [Source(channel=i + 1, position=tuple(points[i]), radius=1000,
                   direction_degrees=(0.0 if directional else None))
            for i in range(10)]


def test_complete_q3_policy_clears_all_sources_without_hidden_count():
    points = q3_search_points()
    sources = _near_sources(points + points)
    arena = OfflineArena(sources, error_seed=3)
    result = run_mission(arena, "q3")
    assert arena.cleared_sources == arena.total_sources == 10
    assert result.cleared_channels == list(range(1, 11))
    assert result.search_points_completed == 7


def test_complete_q4_policy_uses_direction_independent_fallback():
    route = q4_search_points()
    interior = [candidate for candidate in route if np.linalg.norm(candidate) <= 1700][:10]
    sources = _near_sources(interior, directional=True)
    # Make one target require a normal direction reply and optical fallback.
    sources[0].position = tuple(interior[0] + np.array([100.0, 0.0]))
    sources[0].direction_degrees = 180.0
    arena = OfflineArena(sources, error_seed=4)
    result = run_mission(arena, "q4")
    assert arena.cleared_sources == arena.total_sources == 10
    assert result.fallback_channels >= 1
    assert result.failed_clears >= 1
