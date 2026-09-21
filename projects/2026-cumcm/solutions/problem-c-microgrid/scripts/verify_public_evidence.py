"""Check that the public result summary is represented in the paper."""
from __future__ import annotations

import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


def verify() -> None:
    summary = json.loads((PROJECT / "results/paper-summary.json").read_text(encoding="utf-8"))
    paper = (PROJECT / "paper/paper.md").read_text(encoding="utf-8")
    expected = {
        f'{summary["q1"]["cost_yuan"]:.2f}': "Q1 cost",
        f'{summary["q2"]["total_cost_yuan"] / 10000:.2f}万元': "Q2 cost",
        f'{summary["q3"]["total_cost_yuan"] / 10000:.2f}万元': "Q3 cost",
        f'{summary["q4"]["q4_2_cost_yuan"] / 10000:.2f}': "Q4-2 cost",
        f'{summary["q4"]["q4_3_cost_yuan"] / 10000:.2f}万元': "Q4-3 cost",
    }
    missing = [label for text, label in expected.items() if text not in paper]
    if missing:
        raise AssertionError("Paper is missing summary claims: " + ", ".join(missing))


if __name__ == "__main__":
    verify()
    print("Public paper evidence is synchronized.")
