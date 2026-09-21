"""Run the complete strategy against an already-open official simulator test."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mission import run_mission
from robot_api import RobotAPI


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("q3", "q4"), required=True)
    parser.add_argument("--robot-id", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:2026")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    api = RobotAPI(args.robot_id, base_url=args.base_url)
    entered = api.enter()
    result = run_mission(api, args.mode)
    exited = api.exit()
    payload = {"scope": "official simulator response summary", "enter": entered,
               "mission": result.to_dict(), "exit": exited}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
