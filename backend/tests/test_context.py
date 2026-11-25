from datetime import datetime, timezone

import pytest

from app import context
from app.context import Asset, RainAnomaly, nearby_assets, priority, rain_anomaly
from app.reasoning import Observation, SignalType

NOVEMBER = datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
JULY = datetime(2026, 7, 25, 12, tzinfo=timezone.utc)


def rain(value, when=NOVEMBER, lat=19.006, lon=72.842, kind=SignalType.RAINFALL):
    return Observation(1, kind, lat, lon, value, when)


@pytest.fixture
def assets(monkeypatch):
    def use(*items):
        monkeypatch.setattr(
            context, "_ASSETS", [dict(zip(("kind", "name", "points"), i)) for i in items]
        )
        nearby_assets.cache_clear()

    yield use
    nearby_assets.cache_clear()


def test_same_rain_is_extreme_in_november_but_normal_in_the_monsoon():
    assert rain_anomaly(rain(6)).level == "extreme"
    assert rain_anomaly(rain(6, JULY)) is None
    assert rain_anomaly(rain(10, JULY)).level == "unusual"
    assert rain_anomaly(rain(40, JULY)).level == "extreme"


def test_anomaly_needs_evidence_level_rain_near_the_history():
    assert rain_anomaly(rain(1)) is None
    assert rain_anomaly(rain(40, lat=28.6, lon=77.2)) is None
    assert rain_anomaly(rain(40, kind=SignalType.TRAFFIC)) is None


def test_month_is_taken_in_indian_time():
    # 20:00 UTC on 30 September is already 1 October in Mumbai
    edge = datetime(2026, 9, 30, 20, tzinfo=timezone.utc)
    assert "October" in rain_anomaly(rain(60, edge)).detail


def test_nearest_asset_of_each_kind_within_range(assets):
    assets(
        ("hospital", "Near", [[19.002, 72.8]]),
        ("hospital", "Nearer", [[19.001, 72.8]]),
        ("hospital", "Too far", [[19.01, 72.8]]),
        ("railway station", "Station", [[19.003, 72.8]]),
    )
    assert [a.name for a in nearby_assets(19.0, 72.8)] == ["Nearer", "Station"]


def test_road_distance_is_to_the_line_not_its_ends(assets):
    assets(("major road", "Long road", [[19.001, 72.7], [19.001, 72.7], [19.001, 72.9]]))
    (road,) = nearby_assets(19.0, 72.8)
    assert road.distance_m == 111


def test_priority_adds_context_and_explains_it():
    hospital = Asset("hospital", "A", 100, 0, 0)
    result = priority(0.95, [hospital], RainAnomaly("unusual", "x"))
    assert (result.level, result.value) == ("high", 1.05)
    assert len(result.reasons) == 3
    assert priority(0.65, [], None).level == "low"
    assert priority(0.7, [hospital], None).level == "medium"


def test_bundled_data_is_usable():
    assert {a["kind"] for a in context._ASSETS} == {
        "hospital", "fire station", "railway station", "major road",
    }
    assert all(a["points"] and a["name"] for a in context._ASSETS)
    assert all(len(p["months"]) == 12 for p in context._RAIN_HISTORY)
