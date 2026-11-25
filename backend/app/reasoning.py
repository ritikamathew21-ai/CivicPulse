"""Deterministic cross-signal reasoning. Pure functions: no database, clock or network.

1. Drop signals too weak to be evidence.
2. Pair signals that are close in space AND time.
3. Group them around anchors. A group's members must all align with one anchor, so a
   chain of neighbours cannot stretch a single event across the whole city.
4. Score each group holding at least two signal types, and keep the reasons.

The score is an engineering score, not a probability.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from itertools import combinations
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0


class SignalType(StrEnum):
    RAINFALL = "rainfall"
    TRAFFIC = "traffic"
    INCIDENT = "incident"


@dataclass(frozen=True)
class Observation:
    id: int
    type: SignalType
    lat: float
    lon: float
    value: float
    observed_at: datetime


@dataclass(frozen=True)
class Evidence:
    factor: str
    weight: float
    points: float
    detail: str


@dataclass(frozen=True)
class Hypothesis:
    id: str
    anchor: Observation
    title: str
    score: float
    members: tuple[Observation, ...]
    aligned_pairs: int
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class Analysis:
    hypotheses: list[Hypothesis]
    reasons: dict[int, str]


WEIGHTS = {
    SignalType.RAINFALL: 0.30,
    SignalType.TRAFFIC: 0.25,
    SignalType.INCIDENT: 0.20,
}
SPATIAL_WEIGHT = 0.10
TEMPORAL_WEIGHT = 0.10

# Below these a reading is normal background, not evidence
THRESHOLDS = {
    SignalType.RAINFALL: (2.5, "mm/h"),
    SignalType.TRAFFIC: (30.0, "% slowdown"),
    SignalType.INCIDENT: (1.0, "severity"),
}
LABELS = {
    SignalType.RAINFALL: "Rainfall",
    SignalType.TRAFFIC: "Traffic slowdown",
    SignalType.INCIDENT: "Road incident",
}


def distance_km(a: Observation, b: Observation) -> float:
    lat1, lat2 = radians(a.lat), radians(b.lat)
    h = (
        sin((lat2 - lat1) / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(radians(b.lon - a.lon) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * asin(min(1.0, sqrt(h)))


def gap_minutes(a: Observation, b: Observation) -> float:
    return abs((a.observed_at - b.observed_at).total_seconds()) / 60


def analyse(
    observations: Sequence[Observation], radius_km: float, window_min: float
) -> Analysis:
    reasons: dict[int, str] = {}
    strong: list[Observation] = []
    for obs in observations:
        threshold, unit = THRESHOLDS[obs.type]
        if obs.value < threshold:
            reasons[obs.id] = (
                f"{obs.value:g} {unit} is below the evidence threshold of {threshold:g}"
            )
        else:
            strong.append(obs)

    hypotheses = [
        _build_hypothesis(anchor, members, radius_km, window_min)
        for anchor, members in _group(strong, radius_km, window_min)
    ]
    hypotheses.sort(key=lambda h: (-h.score, -len(h.members), h.anchor.id))

    for hyp in hypotheses:
        for member in hyp.members:
            reasons[member.id] = (
                "Anchor of this event"
                if member is hyp.anchor
                else f"{distance_km(member, hyp.anchor):.2f} km and "
                f"{gap_minutes(member, hyp.anchor):.0f} min from the event anchor"
            )
    for obs in strong:
        if obs.id not in reasons:
            reasons[obs.id] = _exclusion_reason(obs, hypotheses, radius_km, window_min)
    return Analysis(hypotheses, reasons)


def _group(
    observations: Sequence[Observation], radius_km: float, window_min: float
) -> list[tuple[Observation, list[Observation]]]:
    by_id = {o.id: o for o in observations}
    neighbours: dict[int, set[int]] = {i: set() for i in by_id}
    for a, b in combinations(observations, 2):
        if gap_minutes(a, b) <= window_min and distance_km(a, b) <= radius_km:
            neighbours[a.id].add(b.id)
            neighbours[b.id].add(a.id)

    def types_around(i: int) -> int:
        return len({by_id[j].type for j in neighbours[i] | {i}})

    def spread(i: int) -> float:
        return sum(distance_km(by_id[i], by_id[j]) for j in sorted(neighbours[i]))

    remaining = set(by_id)
    groups = []
    while remaining:
        anchor_id = max(
            remaining,
            key=lambda i: (types_around(i), len(neighbours[i]), -spread(i), -i),
        )
        if types_around(anchor_id) < 2:
            break  # nothing cross-signal is left
        member_ids = neighbours[anchor_id] | {anchor_id}
        groups.append((by_id[anchor_id], [by_id[i] for i in sorted(member_ids)]))
        remaining -= member_ids
        for i in remaining:
            neighbours[i] -= member_ids
    return groups


def _build_hypothesis(
    anchor: Observation,
    members: list[Observation],
    radius_km: float,
    window_min: float,
) -> Hypothesis:
    pairs = list(combinations(members, 2))
    near = [distance_km(a, b) <= radius_km for a, b in pairs]
    together = [gap_minutes(a, b) <= window_min for a, b in pairs]

    evidence = []
    for kind in SignalType:
        count = sum(m.type == kind for m in members)
        weight = WEIGHTS[kind]
        evidence.append(
            Evidence(
                LABELS[kind],
                weight,
                weight if count else 0.0,
                f"{count} signal{'' if count == 1 else 's'} in the aligned region"
                if count
                else "Not detected in the aligned region",
            )
        )
    # Alignment points scale with the share of member pairs that line up with each other
    for factor, weight, hits, limit in (
        ("Spatial alignment", SPATIAL_WEIGHT, near, f"{radius_km:g} km"),
        ("Temporal alignment", TEMPORAL_WEIGHT, together, f"{window_min:g} min"),
    ):
        evidence.append(
            Evidence(
                factor,
                weight,
                round(weight * sum(hits) / len(hits), 4),
                f"{sum(hits)} of {len(hits)} signal pairs within {limit}",
            )
        )

    return Hypothesis(
        id=f"H-{anchor.id}",
        anchor=anchor,
        title=_title({m.type for m in members}),
        score=round(sum(e.points for e in evidence), 4),
        members=tuple(members),
        aligned_pairs=sum(n and t for n, t in zip(near, together)),
        evidence=tuple(evidence),
    )


def _title(types: set[SignalType]) -> str:
    if {SignalType.RAINFALL, SignalType.TRAFFIC} <= types:
        return "Possible weather-related traffic disruption"
    if SignalType.RAINFALL in types:
        return "Possible weather-related road incident"
    return "Possible incident-related traffic disruption"


def _exclusion_reason(
    obs: Observation,
    hypotheses: list[Hypothesis],
    radius_km: float,
    window_min: float,
) -> str:
    if not hypotheses:
        return f"No other signal type within {radius_km:g} km and {window_min:g} min"
    nearest = min(
        (h.anchor for h in hypotheses),
        key=lambda a: (distance_km(obs, a), gap_minutes(obs, a)),
    )
    failures = []
    distance, gap = distance_km(obs, nearest), gap_minutes(obs, nearest)
    if distance > radius_km:
        failures.append(f"{distance:.1f} km away (limit {radius_km:g} km)")
    if gap > window_min:
        failures.append(f"{gap:.0f} min apart (limit {window_min:g} min)")
    return "Nearest event: " + " and ".join(failures)
