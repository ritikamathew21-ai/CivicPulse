"""Rebuilds app/data/*.json from OpenStreetMap and Open-Meteo. Run: python -m scripts.build_context [name ...]"""

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

from app.weather import MONITORED_POINTS

DATA = Path(__file__).parents[1] / "app" / "data"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
BBOX = "18.88,72.77,19.30,72.99"
KINDS = {
    "hospital": 'nwr["amenity"="hospital"]["name"]',
    "fire station": 'nwr["amenity"="fire_station"]',
    "railway station": 'nwr["railway"="station"]["name"]',
    "major road": 'way["highway"~"^(motorway|trunk|primary)$"]["name"]',
}
FIRST_YEAR, LAST_YEAR = 2016, 2025


def overpass(query: str) -> list[dict]:
    for wait in [60] * 20 + [0]:  # the free public server is often briefly overloaded
        response = httpx.post(
            OVERPASS_URL,
            data={"data": query},
            headers={"User-Agent": "civicpulse-data-build/1.0"},
            timeout=150,
        )
        if response.status_code not in (429, 502, 503, 504):
            break
        time.sleep(wait)
    response.raise_for_status()
    return response.json()["elements"]


def infrastructure() -> list[dict]:
    assets = []
    for kind, query in KINDS.items():
        is_road = kind == "major road"
        query = f"[out:json][timeout:120];{query}({BBOX});out {'geom' if is_road else 'center'};"
        for element in overpass(query):
            tags = element["tags"]
            if is_road:
                points = [(p["lat"], p["lon"]) for p in element["geometry"]]
            else:
                where = element.get("center", element)
                points = [(where["lat"], where["lon"])]
            assets.append(
                {
                    "kind": kind,
                    "name": tags.get("name:en") or tags.get("name") or "Fire station",
                    "points": [[round(lat, 5), round(lon, 5)] for lat, lon in points],
                }
            )
    return assets


def rainfall_history() -> list[dict]:
    response = httpx.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": ",".join(str(lat) for lat, _ in MONITORED_POINTS),
            "longitude": ",".join(str(lon) for _, lon in MONITORED_POINTS),
            "start_date": f"{FIRST_YEAR}-01-01",
            "end_date": f"{LAST_YEAR}-12-31",
            "hourly": "precipitation",
            "timezone": "Asia/Kolkata",
        },
        timeout=180,
    )
    response.raise_for_status()
    places = []
    for (lat, lon), place in zip(MONITORED_POINTS, response.json(), strict=True):
        hours = defaultdict(list)
        for hour, rain in zip(place["hourly"]["time"], place["hourly"]["precipitation"], strict=True):
            if rain is not None:
                hours[int(hour[5:7])].append(rain)
        months = {}
        for month, values in sorted(hours.items()):
            values.sort()
            at = lambda q: values[min(len(values) - 1, int(q * len(values)))]
            months[month] = {"hours": len(values), "p99": at(0.99), "p999": at(0.999)}
        places.append({"lat": lat, "lon": lon, "months": months})
    return places


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    builders = {"infrastructure": infrastructure, "rainfall_history": rainfall_history}
    for name in sys.argv[1:] or builders:
        content = builders[name]()
        path = DATA / f"{name}.json"
        path.write_text(json.dumps(content, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(path.name, len(content), "entries", path.stat().st_size // 1024, "KB")
