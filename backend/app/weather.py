"""Live rainfall from Open-Meteo, a free weather model service that needs no API key."""

from collections.abc import Iterable
from datetime import datetime, timezone

import httpx

from .config import settings

Point = tuple[float, float]

MONITORED_POINTS: list[Point] = [
    (18.9220, 72.8347),  # Colaba
    (19.0060, 72.8420),  # Hindmata
    (19.0670, 72.8690),  # BKC
    (19.1190, 72.8465),  # Andheri
    (19.2290, 72.8570),  # Borivali
]
MAX_POINTS = 25


def points_to_sample(report_locations: Iterable[Point]) -> list[Point]:
    """Monitored points, plus places with recent reports so rain can align with them."""
    rounded = [(round(lat, 3), round(lon, 3)) for lat, lon in report_locations]
    return list(dict.fromkeys(MONITORED_POINTS + rounded))[:MAX_POINTS]


def fetch_rainfall(points: list[Point]) -> list[dict]:
    response = httpx.get(
        settings.open_meteo_url,
        params={
            "latitude": ",".join(str(lat) for lat, _ in points),
            "longitude": ",".join(str(lon) for _, lon in points),
            "current": "precipitation",
            "timezone": "UTC",
        },
        timeout=10,
    )
    response.raise_for_status()
    return parse(points, response.json())


def parse(points: list[Point], payload: list | dict) -> list[dict]:
    places = payload if isinstance(payload, list) else [payload]
    readings = []
    for (lat, lon), place in zip(points, places, strict=True):
        current = place["current"]
        # precipitation is the total over `interval` seconds; convert it to mm/h
        rate = current["precipitation"] * 3600 / current["interval"]
        readings.append(
            {
                "lat": lat,
                "lon": lon,
                "value": round(rate, 2),
                "observed_at": datetime.fromisoformat(current["time"]).replace(
                    tzinfo=timezone.utc
                ),
                "external_id": f"open-meteo:{lat}:{lon}:{current['time']}",
            }
        )
    return readings
