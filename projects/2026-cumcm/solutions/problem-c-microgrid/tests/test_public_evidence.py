from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT / "scripts"))

from optimizer import Battery, plan
from q3 import revision_cost
from q4_prices import price_forecast
from verify_public_evidence import verify


def test_public_summary_is_synchronized_with_paper() -> None:
    verify()


def test_storage_efficiency_contract() -> None:
    battery = Battery(0.9, 0.9)
    result = plan([0.0, 100.0], [1.0, 10.0], 1200.0, battery, terminal=1200.0)
    np.testing.assert_allclose(result["cost"], result["dual_cost"], atol=1e-9, rtol=0)
    np.testing.assert_allclose(np.diff(result["soc"]), 0.9 * result["charge"] - result["discharge"] / 0.9)


def test_sequential_revision_cost_uses_effective_order() -> None:
    total = 100.0 + revision_cost(100.0, 80.0, 1.0) + revision_cost(80.0, 100.0, 1.0)
    assert total == 120.0


def test_price_forecast_uses_history_prefix() -> None:
    history = np.arange(10 * 144, dtype=float) / 1000 + 0.3
    origin = len(history)
    targets = np.arange(origin, origin + 288)
    forecast = price_forecast(history, origin, targets, "weekly_mean")
    assert np.isfinite(forecast).all()
    with np.testing.assert_raises(AssertionError):
        price_forecast(np.r_[history, 9.0], origin, targets, "weekly_mean")
