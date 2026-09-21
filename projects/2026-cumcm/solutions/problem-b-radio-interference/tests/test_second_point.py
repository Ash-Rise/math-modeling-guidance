import math

import numpy as np
import pytest

from radio_geometry import Bearing, localization_region
from second_point import (guaranteed_candidate_region, local_point, reception_margin,
                          response_diameter_upper, second_point_options, synthetic_reply, two_bearing_region)


def test_four_disk_domain_uses_information_from_first_reception():
    first = Bearing((0, 0), 0)
    q = np.array([400., 400.])
    assert reception_margin(first, q) > 0
    assert guaranteed_candidate_region(first).contains(q)
    assert np.linalg.norm(q - [1500, 0]) > 1000  # Old A_1000 would wrongly reject as a candidate.
    assert reception_margin(first, [0, 500]) < 0
    for rho in (5.00001, 100, 500, 1000, 1250, 1500):
        for delta in (-1, 0, 1):
            g = rho * np.array([math.cos(math.radians(delta)), math.sin(math.radians(delta))])
            assert synthetic_reply(g, max(1000, rho), q, 0)["result"] != "no_signal"


def test_candidate_is_rotation_translation_equivariant():
    first = Bearing((250, -700), 127)
    origin = Bearing((0, 0), 0)
    q = local_point(first, 400, -400)
    assert reception_margin(first, q) == pytest.approx(reception_margin(origin, (400, -400)))


def test_truth_containment_all_legal_updates_and_near_branch():
    first = Bearing((0, 0), 0)
    q = local_point(first, 700, 600)
    for rho in (5.001, 20, 200, 700, 1000, 1499.99, 1500):
        for delta in (-1, -0.25, 0, 0.75, 1):
            g = rho * np.array([math.cos(math.radians(delta)), math.sin(math.radians(delta))])
            assert localization_region([first], reception_bound=1500).contains(g)
            for bias in (-1, 0, 1):
                reply = synthetic_reply(g, max(1000, rho), q, bias)
                assert reply["result"] == "direction"
                region = two_bearing_region(first, q, reply["degrees"])
                assert region.contains(g)
                circle = region.enclosing_circle()
                assert np.linalg.norm(g - circle.center) <= circle.radius_upper
                if circle.clearance() == "guaranteed":
                    assert np.linalg.norm(g - circle.center) <= 20
    assert synthetic_reply((5, 0), 1000, (0, 0), 1)["result"] == "near"
    assert synthetic_reply((20, 0), 1000, (0, 0), 0)["result"] == "direction"


def test_quantized_boundary_observations_respect_the_given_error_bound():
    # Construct truth around a two-decimal *returned* angle. Do not round a noisy
    # angle past +/-1 and then silently enlarge the official physical error.
    for reported in (0., 0.01, 359.99):
        for error in (-1., 1.):
            angle = math.radians(reported - error)
            truth = 1500 * np.array([math.cos(angle), math.sin(angle)])
            assert localization_region([Bearing((0, 0), reported)], reception_bound=1500).contains(truth)


def test_reception_boundary_and_actual_signal_loss_control():
    for radius in (1000., 1500.):
        for degrees in (-1., 0., 1., 127.):
            direction = np.array([math.cos(math.radians(degrees)), math.sin(math.radians(degrees))])
            assert synthetic_reply(radius * direction, radius, (0, 0), 0)["result"] == "direction"
            assert synthetic_reply((radius + 0.001) * direction, radius, (0, 0), 0)["result"] == "no_signal"
    assert synthetic_reply((1500, 0), 1500, (0, 500), 0)["result"] == "no_signal"


def test_synthetic_replies_are_two_decimal_and_physically_legal():
    for angle in (0., 0.0049, 0.0051, 127.9999, 359.9949, 359.9999):
        for bias in (-1., -0.333, 0., 0.777, 1.):
            direction = np.array([math.cos(math.radians(angle)), math.sin(math.radians(angle))])
            report = synthetic_reply(1000 * direction, 1000, (0, 0), bias)["degrees"]
            assert abs(report * 100 - round(report * 100)) < 1e-8
            error = (report - angle + 180) % 360 - 180
            assert -1 - 1e-10 <= error <= 1 + 1e-10
            assert abs(error - bias) < 0.010001
        assert synthetic_reply(5 * direction, 1000, (0, 0), 0)["result"] == "near"


def test_continuous_response_bound_covers_legal_observations_including_axis_candidate():
    first = Bearing((0, 0), 0)
    for q in ((400, 400), (800, 600), (400, 0)):
        bound = response_diameter_upper(first, q, 2)["diameter_upper_m"]
        for distance in (5.001, 513., 1000., 1500.):
            for offset in (-1., -0.3, 1.):
                truth = distance * np.array([math.cos(math.radians(offset)), math.sin(math.radians(offset))])
                for bias in (-1., 0.2, 1.):
                    reply = synthetic_reply(truth, max(1000, distance), q, bias)
                    assert reply["result"] == "direction"
                    assert two_bearing_region(first, q, reply["degrees"]).diameter().value <= bound + 1e-6


def test_budget_selection_is_explicit_and_preserves_reception():
    first = Bearing((0, 0), 0)
    options = [(0, 0), (0, 500), (400, 400), (400, -400), (800, 600)]
    result = second_point_options(first, options, bin_degrees=2, move_budget=600)
    assert result["best_with_supplied_budget"] is not None
    assert all(row["move_m"] <= 600 and row["reception_margin_m"] >= 0 for row in result["pareto"])
    assert all(abs(row["lateral_m"]) == 400 for row in result["pareto"])
    assert second_point_options(first, [], bin_degrees=2)["best_with_supplied_budget"] is None
    assert not second_point_options(first, options, bin_degrees=2, move_budget=10)["pareto"]
    with pytest.raises(ValueError):
        second_point_options(Bearing((4000, 0), 0), options)


def test_clipped_domain_and_robot_outside_target_keep_truth():
    for position, angle, distance in (((1600, 0), 90, 600), ((2200, 0), 180, 700), ((1600, 0), 180, 1500)):
        first = Bearing(position, angle)
        truth = local_point(first, distance, 0)
        assert np.linalg.norm(truth) <= 1800
        for sign in (-1, 1):
            q = local_point(first, 600, sign * 500)
            for bias in (-1., 0., 1.):
                reply = synthetic_reply(truth, max(1000, distance), q, bias)
                assert reply["result"] == "direction"
                region = two_bearing_region(first, q, reply["degrees"])
                assert region.contains(truth)
                circle = region.enclosing_circle()
                assert np.linalg.norm(truth - circle.center) <= circle.radius_upper
