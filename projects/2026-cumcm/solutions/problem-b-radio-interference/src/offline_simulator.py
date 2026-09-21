"""Small rule-faithful offline arena for deterministic Q3/Q4 stress tests.

It implements the public geometry and timing rules only. It is not the official
simulator and intentionally makes no claim about the hidden case distribution.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math

import numpy as np

from radio_geometry import point, unit


@dataclass
class Source:
    channel: int
    position: tuple[float, float]
    radius: float
    direction_degrees: float | None = None
    cleared: bool = False

    def __post_init__(self):
        self.position = tuple(point(self.position))
        if not 1 <= self.channel <= 20:
            raise ValueError("Channel must be in 1..20")
        if not 1000.0 <= self.radius <= 1500.0:
            raise ValueError("Reception radius must be in [1000, 1500]")
        if np.linalg.norm(point(self.position)) > 1800.0 + 1e-8:
            raise ValueError("Source must lie inside the target disk")


class OfflineArena:
    """Synchronous backend with the same measure/clear semantics used by missions."""

    def __init__(self, sources: list[Source], *, error_seed: int = 0):
        if len({source.channel for source in sources}) != len(sources):
            raise ValueError("Source channels must be unique")
        if not 10 <= len(sources) <= 16:
            raise ValueError("Official cases contain 10..16 sources")
        self.sources = {source.channel: source for source in sources}
        self.error_seed = int(error_seed)
        self.position = np.zeros(2)
        self.current_channel = 1
        self.virtual_time_s = 0.0
        self.measure_requests = 0
        self.clear_requests = 0
        self.failed_clears = 0

    @property
    def total_sources(self) -> int:
        return len(self.sources)

    @property
    def cleared_sources(self) -> int:
        return sum(source.cleared for source in self.sources.values())

    def _move(self, destination) -> None:
        destination = point(destination)
        self.virtual_time_s += float(np.linalg.norm(destination - self.position)) / 5.0
        self.position = destination

    def _fixed_error(self, source: Source, location) -> float:
        location = point(location)
        token = f"{self.error_seed}|{source.channel}|{location[0]:.6f}|{location[1]:.6f}".encode()
        raw = int.from_bytes(hashlib.blake2b(token, digest_size=8).digest(), "big")
        return -0.995 + 1.99 * raw / (2**64 - 1)

    @staticmethod
    def _covered(source: Source, location) -> bool:
        delta = point(location) - point(source.position)
        if np.linalg.norm(delta) > source.radius + 1e-8:
            return False
        return (source.direction_degrees is None or
                float(unit(source.direction_degrees) @ delta) >= -1e-8)

    def measure(self, location, channel: int) -> dict:
        self._move(location)
        if channel != self.current_channel:
            self.virtual_time_s += 1.0
        self.current_channel = channel
        self.virtual_time_s += 5.0
        self.measure_requests += 1
        source = self.sources.get(channel)
        if source is None or source.cleared or not self._covered(source, location):
            return {"result": "no_signal"}
        delta = point(source.position) - self.position
        distance = float(np.linalg.norm(delta))
        if distance <= 5.0 + 1e-8:
            return {"result": "near"}
        true_angle = math.degrees(math.atan2(delta[1], delta[0]))
        degrees = round((true_angle + self._fixed_error(source, location)) % 360.0, 2) % 360.0
        error = (degrees - true_angle + 180.0) % 360.0 - 180.0
        assert abs(error) <= 1.0 + 1e-10
        return {"result": "direction", "degrees": degrees}

    def clear(self, location, channel: int) -> dict:
        self._move(location)
        self.clear_requests += 1
        source = self.sources.get(channel)
        success = (source is not None and not source.cleared and
                   np.linalg.norm(point(source.position) - self.position) <= 20.0 + 1e-8)
        self.virtual_time_s += 5.0 if success else 3.0
        if success:
            source.cleared = True
            return {"result": "success"}
        self.failed_clears += 1
        return {"result": "no_target_in_range"}
