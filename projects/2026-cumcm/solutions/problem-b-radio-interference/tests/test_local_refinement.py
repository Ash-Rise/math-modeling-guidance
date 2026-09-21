import numpy as np
import pytest

from local_refinement import bearing_update, guaranteed_reception_margin, local_probe_options
from radio_geometry import Bearing, localization_region
from second_point import synthetic_reply, two_bearing_region


def two_reading_case(truth=(1000.0, 0.0), second=(550.0, 575.0)):
    first = Bearing((0.0, 0.0), 0.0)
    reply = synthetic_reply(truth, 1000.0, second, 0.0)
    assert reply["result"] == "direction"
    return two_bearing_region(first, second, reply["degrees"]), np.asarray(second), np.asarray(truth)


def test_follow_up_candidates_guarantee_reception_and_reduce_worst_radius():
    prior, current, truth = two_reading_case()
    options = local_probe_options(prior, current, radii=(150.0, 300.0, 500.0),
                                  directions=12, move_budget=700.0, bin_degrees=5.0)
    chosen = options["best_with_supplied_budget"]
    assert chosen is not None
    assert chosen["reception_margin_m"] >= -1e-6
    assert chosen["radius_upper_m"] < options["prior_radius_upper_m"]
    assert guaranteed_reception_margin(prior, chosen["position"]) >= -1e-6
    assert np.linalg.norm(truth - chosen["position"]) <= 1000.0 + 1e-6


def test_actual_follow_up_is_contained_by_certified_response_bound():
    prior, current, truth = two_reading_case((1200.0, 10.0))
    chosen = local_probe_options(prior, current, radii=(200.0, 400.0), directions=8,
                                 move_budget=700.0, bin_degrees=5.0)["best_with_supplied_budget"]
    reply = synthetic_reply(truth, 1500.0, chosen["position"], 1.0)
    assert reply["result"] == "direction"
    posterior = bearing_update(prior, chosen["position"], reply["degrees"])
    assert posterior.contains(truth)
    assert posterior.enclosing_circle().radius_upper <= chosen["radius_upper_m"] + 1e-5


def test_budget_and_input_contracts_are_explicit():
    prior = localization_region([Bearing((0, 0), 0)], reception_bound=1500)
    assert not local_probe_options(prior, (0, 0), radii=(100,), directions=4,
                                   move_budget=10, bin_degrees=10)["pareto"]
    with pytest.raises(ValueError):
        local_probe_options(prior, (0, 0), move_budget=-1)
