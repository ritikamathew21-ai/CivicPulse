"""Simulated Mumbai scenarios. Only raw signals live here; every result is computed."""

from datetime import datetime, timedelta
from enum import StrEnum

from .models import Signal
from .reasoning import SignalType
from .schemas import Dataset

R, T, I = SignalType.RAINFALL, SignalType.TRAFFIC, SignalType.INCIDENT
GAUGE, FEED, CITIZEN = (
    "Rain gauge (simulated)",
    "Traffic feed (simulated)",
    "Citizen report (simulated)",
)


class Scenario(StrEnum):
    SINGLE = "single"
    MULTI = "multi"


# type, lat, lon, value, minutes ago, source, description
_SINGLE = [
    (R, 19.0083, 72.8402, 38.0, 14, GAUGE, "Heavy rain near Hindmata"),
    (R, 19.0058, 72.8437, 42.5, 10, GAUGE, "Heavy rain, Dadar East"),
    (R, 19.0041, 72.8447, 35.2, 6, GAUGE, "Heavy rain, Parel side"),
    (T, 19.0088, 72.8424, 62.0, 9, FEED, "Slowdown on Dr Ambedkar Road"),
    (T, 19.0062, 72.8413, 71.0, 7, FEED, "Queue at Hindmata junction"),
    (T, 19.0045, 72.8404, 55.0, 4, FEED, "Slow traffic towards Parel"),
    (I, 19.0077, 72.8442, 3.0, 5, CITIZEN, "Car stalled in standing water"),
    (I, 19.0039, 72.8430, 4.0, 3, CITIZEN, "Waterlogging, two lanes blocked"),
    (T, 19.2290, 72.8570, 45.0, 6, FEED, "Slow traffic at Borivali"),
]

_EXTRA = [
    (T, 19.0660, 72.8680, 66.0, 11, FEED, "Slowdown on BKC connector"),
    (T, 19.0675, 72.8700, 58.0, 8, FEED, "Queue at BKC junction"),
    (I, 19.0668, 72.8692, 4.0, 7, CITIZEN, "Two-vehicle collision"),
    (R, 19.1190, 72.8465, 24.0, 12, GAUGE, "Rain at Andheri"),
    (I, 19.1202, 72.8480, 2.0, 5, CITIZEN, "Fallen branch on road"),
    (T, 19.0060, 72.8420, 50.0, 140, FEED, "Earlier slowdown at Hindmata"),
    (R, 18.9220, 72.8347, 0.6, 8, GAUGE, "Drizzle at Colaba"),
]


def build(scenario: Scenario, now: datetime) -> list[Signal]:
    rows = _SINGLE + (_EXTRA if scenario is Scenario.MULTI else [])
    return [
        Signal(
            dataset=Dataset.DEMO,
            type=kind,
            lat=lat,
            lon=lon,
            value=value,
            observed_at=now - timedelta(minutes=minutes_ago),
            source=source,
            description=description,
        )
        for kind, lat, lon, value, minutes_ago, source, description in rows
    ]
