"""Synchronous HTTP+JSON client for the official four-action interface."""
from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

import numpy as np

from radio_geometry import point


class RobotAPI:
    def __init__(self, robot_id: str, *, base_url="http://127.0.0.1:2026", timeout=5.0, retries=2):
        if not robot_id:
            raise ValueError("robot_id is required")
        self.robot_id = robot_id
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self.retries = int(retries)
        self.sequence = 0
        self.position = np.zeros(2)
        self.current_channel = 1
        self.virtual_time_s = 0.0
        self.measure_requests = 0
        self.clear_requests = 0
        self.failed_clears = 0

    def _base(self, request_id: str) -> dict:
        return {"arena_id": "default", "robot_id": self.robot_id, "request_id": request_id}

    def _post(self, path: str, payload: dict) -> dict:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        error = None
        for _ in range(self.retries + 1):
            try:
                request = Request(self.base_url + path, data=body,
                                  headers={"Content-Type": "application/json"}, method="POST")
                with urlopen(request, timeout=self.timeout) as response:
                    result = json.loads(response.read().decode("utf-8"))
                if result.get("accepted") is not True:
                    raise RuntimeError(f"Action rejected: {result}")
                return result
            except URLError as exc:
                error = exc
        raise ConnectionError(f"No response after idempotent retries: {error}")

    def _request(self, prefix: str) -> str:
        self.sequence += 1
        return f"{prefix}-{self.sequence}"

    def enter(self) -> dict:
        return self._post("/enter", self._base(self._request("enter")))

    def exit(self) -> dict:
        return self._post("/exit", self._base(self._request("exit")))

    def measure(self, location, channel: int) -> dict:
        location = point(location)
        payload = self._base(self._request("measure"))
        payload.update(position={"x": float(location[0]), "y": float(location[1])}, channel=int(channel))
        response = self._post("/measure", payload)
        self.position = location
        self.current_channel = int(channel)
        self.virtual_time_s = float(response["virtual_time_s"])
        self.measure_requests += 1
        result = {"result": response["measure_result"]}
        if result["result"] == "direction":
            result["degrees"] = float(response["svd_deg"])
        return result

    def clear(self, location, channel: int) -> dict:
        location = point(location)
        payload = self._base(self._request("clear"))
        payload.update(position={"x": float(location[0]), "y": float(location[1])}, channel=int(channel))
        response = self._post("/clear", payload)
        self.position = location
        self.virtual_time_s = float(response["virtual_time_s"])
        self.clear_requests += 1
        result = "success" if response["clear_result"] == "success" else "no_target_in_range"
        self.failed_clears += int(result != "success")
        return {"result": result}
