"""Check cost semantics independently of the enumeration implementation."""
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "canteen_example", Path(__file__).resolve().parents[1] / "run.py"
)
MODEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODEL)


class CanteenModelTest(unittest.TestCase):
    def test_marginal_cost_matches_one_extra_meal(self):
        demands = [0, 2, 2, 4]
        rows, _ = MODEL.optimize(demands, 6, 1, 3)
        self.assertEqual(rows[0][1], 3 * sum(demands))
        for q in range(6):
            marginal = sum(1 if d <= q else -3 for d in demands)
            self.assertEqual(rows[q + 1][1] - rows[q][1], marginal)

    def test_ties_and_capacity_are_preserved(self):
        self.assertEqual(MODEL.optimize([0, 2], 3, 1, 1)[1], [0, 1, 2])
        self.assertEqual(MODEL.optimize([0, 2], 3, 1, 3)[1], [2])
        self.assertEqual(MODEL.optimize([0, 2], 1, 1, 3)[1], [1])
        self.assertEqual(MODEL.optimize([0, 2], 0, 1, 3)[1], [0])

    def test_invalid_scenarios_and_costs_are_rejected(self):
        for demands, capacity, waste, shortage in (
            ([], 140, 3, 9), ([-1], 140, 3, 9),
            ([1], -1, 3, 9), ([1], 140, 0, 9), ([1], 140, 3, 0),
        ):
            with self.subTest(demands=demands, capacity=capacity, waste=waste, shortage=shortage):
                with self.assertRaises(ValueError):
                    MODEL.optimize(demands, capacity, waste, shortage)


if __name__ == "__main__":
    unittest.main()
