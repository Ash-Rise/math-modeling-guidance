"""Recompute public A-example results and compare them with frozen values."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(question: str, tolerance: float) -> dict:
    subprocess.run([sys.executable, str(ROOT / "scripts" / f"solve_{question}.py")], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    current = json.loads((ROOT / "results" / "working" / f"{question}.json").read_text(encoding="utf-8"))
    frozen = json.loads((ROOT / "results" / "frozen" / f"{question}.json").read_text(encoding="utf-8"))
    actual = float(current["effective_shielding_duration_s"])
    expected = float(frozen["effective_shielding_duration_s"])
    difference = abs(actual - expected)
    if difference > tolerance:
        raise SystemExit(f"{question} mismatch: {actual:.12f} vs {expected:.12f} (diff {difference:.3g})")
    return {"question": question, "status": "matched", "duration_s": actual, "frozen_duration_s": expected, "absolute_difference_s": difference}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("q1", "q2", "all"), default="q1")
    parser.add_argument("--tolerance", type=float, default=1e-6)
    args = parser.parse_args()
    questions = ("q1", "q2") if args.scope == "all" else (args.scope,)
    print(json.dumps([run(q, args.tolerance) for q in questions], ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
