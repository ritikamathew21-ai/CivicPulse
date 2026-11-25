"""Context around a hypothesis: nearby infrastructure and how unusual the rain is.

Context sets the priority an operator sees. It never changes the reasoning score.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from math import cos, hypot, radians
from pathlib import Path

from .reasoning import THRESHOLDS, Hypothesis, Observation, SignalType

DATA = Path(__file__).parent / "data"
INDIA_TIME = timezone(timedelta(hours=5, minutes=30))
KM_PER_DEGREE = 111.195
NEARBY_KM = 0.5
# A baseline further away than this says nothing useful about a place
HISTORY_KM = 15.0

ASSET_POINTS = 0.05
UNUSUAL_POINTS = 0.05
EXTREME_POINTS = 0.10
HIGH_PRIORITY = 1.0
MEDIUM_PRIORITY = 0.75


@dataclass(frozen=True)
class Asset:
    kind: str
    name: str
    distance_m: int
    lat: float
    lon: float


@dataclass(frozen=True)
class RainAnomaly:
    level: str  # "unusual" or "extreme"
    detail: str


@dataclass(frozen=True)
class Priority:
    level: str  # "high", "medium" or "low"
    value: float
    reasons: tuple[str, ...]


def _load(name: str) -> list[dict]:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


_ASSETS = _load("infrastructure.json")
_RAIN_HISTORY = _load("rainfall_history.json")


def _offset_km(lat: float, lon: float, point: Sequence[float]) -> tuple[float, float]:
    """Flat-earth x, y from (lat, lon) to point; accurate enough over a city."""
    return (
        (point[1] - lon) * KM_PER_DEGREE * cos(radians(lat)),
        (point[0] - lat) * KM_PER_DEGREE,
    )


def _closest(lat: float, lon: float, points: list[list[float]]) -> tuple[float, list[float]]:
    """Distance to, and position of, the closest spot on a point or a line of points."""
    best = (hypot(*_offset_km(lat, lon, points[0])), points[0])
    for a, b in zip(points, points[1:]):
        ax, ay = _offset_km(lat, lon, a)
        bx, by = _offset_km(lat, lon, b)
        length2 = (bx - ax) ** 2 + (by - ay) ** 2
        t = 0.0
        if length2:
            t = min(1.0, max(0.0, -(ax * (bx - ax) + ay * (by - ay)) / length2))
        distance = hypot(ax + t * (bx - ax), ay + t * (by - ay))
        if distance < best[0]:
            best = (distance, [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])])
    return best


@lru_cache(maxsize=1024)
def nearby_assets(lat: float, lon: float) -> tuple[Asset, ...]:
    """The closest asset of each kind within NEARBY_KM, nearest first."""
    nearest: dict[str, Asset] = {}
    for asset in _ASSETS:
        distance, (at_lat, at_lon) = _closest(lat, lon, asset["points"])
        kind = asset["kind"]
        metres = round(distance * 1000)
        if distance <= NEARBY_KM and (
            kind not in nearest or metres < nearest[kind].distance_m
        ):
            nearest[kind] = Asset(kind, asset["name"], metres, at_lat, at_lon)
    return tuple(sorted(nearest.values(), key=lambda a: (a.distance_m, a.kind)))


def rain_anomaly(obs: Observation) -> RainAnomaly | None:
    if obs.type != SignalType.RAINFALL or obs.value < THRESHOLDS[obs.type][0]:
        return None
    distance, place = min(
        ((hypot(*_offset_km(obs.lat, obs.lon, (p["lat"], p["lon"]))), p) for p in _RAIN_HISTORY),
        key=lambda item: item[0],
    )
    if distance > HISTORY_KM:
        return None
    local = obs.observed_at.astimezone(INDIA_TIME)
    month = place["months"][str(local.month)]
    for level, key, share in (("extreme", "p999", "99.9%"), ("unusual", "p99", "99%")):
        if obs.value > month[key]:
            return RainAnomaly(
                level,
                f"{obs.value:g} mm/h is above {share} of {local:%B} hours "
                f"in 2016–2025 ({month[key]:g} mm)",
            )
    return None


def strongest_anomaly(hyp: Hypothesis) -> RainAnomaly | None:
    rain = [m for m in hyp.members if m.type == SignalType.RAINFALL]
    return rain_anomaly(max(rain, key=lambda m: (m.value, -m.id))) if rain else None


def priority(
    score: float, assets: Sequence[Asset], anomaly: RainAnomaly | None
) -> Priority:
    value = score
    reasons = [f"Reasoning score {score:.2f}"]
    for asset in assets:
        value += ASSET_POINTS
        reasons.append(
            f"+{ASSET_POINTS:.2f} {asset.kind} {asset.distance_m} m away: {asset.name}"
        )
    if anomaly:
        points = EXTREME_POINTS if anomaly.level == "extreme" else UNUSUAL_POINTS
        value += points
        reasons.append(f"+{points:.2f} {anomaly.level} rainfall: {anomaly.detail}")
    value = round(value, 4)
    level = (
        "high"
        if value >= HIGH_PRIORITY
        else "medium" if value >= MEDIUM_PRIORITY else "low"
    )
    return Priority(level, value, tuple(reasons))
