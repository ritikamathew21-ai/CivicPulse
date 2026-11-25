from datetime import datetime, timedelta, timezone

import httpx
import pytest


def get(client, **params):
    response = client.get("/api/analysis", params=params)
    assert response.status_code == 200
    return response.json()


def signal(**changes):
    return {
        "dataset": "live",
        "type": "incident",
        "lat": 19.0,
        "lon": 72.8,
        "value": 3,
        "observed_at": datetime.now(timezone.utc).isoformat(),
    } | changes


def test_single_demo_matches_the_deck(client):
    client.post("/api/demo/single")
    data = get(client)
    assert data["stats"] == {"received": 9, "aligned": 8, "excluded": 1, "aligned_pairs": 28}
    (hyp,) = data["hypotheses"]
    assert hyp["score"] == 0.95
    (excluded,) = [s for s in data["signals"] if s["hypothesis_id"] is None]
    assert "limit 1 km" in excluded["reason"]


def test_multi_demo_is_ranked(client):
    client.post("/api/demo/multi")
    data = get(client)
    assert [h["score"] for h in data["hypotheses"]] == [0.95, 0.7, 0.65]
    assert data["stats"]["excluded"] == 3


def test_demo_reload_keeps_live_data(client):
    assert client.post("/api/signals", json=signal()).status_code == 201
    client.post("/api/demo/single")
    client.post("/api/demo/single")
    assert get(client, dataset="live")["stats"]["received"] == 1
    assert get(client)["stats"]["received"] == 9


def test_decision_follows_an_event_as_it_grows(client):
    client.post("/api/demo/single")
    hyp = get(client)["hypotheses"][0]
    decision = {"dataset": "demo", "status": "acknowledged", "signal_ids": hyp["signal_ids"]}
    assert client.post("/api/decisions", json=decision).status_code == 201
    client.post("/api/signals", json=signal(dataset="demo", lat=hyp["lat"], lon=hyp["lon"]))
    hyp = get(client)["hypotheses"][0]
    assert (hyp["status"], hyp["new_signals"]) == ("acknowledged", 1)


@pytest.mark.parametrize(
    "changes",
    [
        {"lat": 91},
        {"type": "earthquake"},
        {"value": 9},
        {"type": "traffic", "value": -1},
        {"observed_at": "2026-11-25T10:00:00"},
        {"observed_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()},
        {"description": "x" * 301},
        {"dataset": "other"},
    ],
)
def test_bad_signals_are_rejected(client, changes):
    assert client.post("/api/signals", json=signal(**changes)).status_code == 422


def test_bad_parameters_are_rejected(client):
    assert client.get("/api/analysis", params={"radius_km": 0}).status_code == 422
    assert client.post("/api/demo/unknown").status_code == 422


def test_rainfall_is_sampled_at_reports_once(client, monkeypatch):
    client.post("/api/signals", json=signal())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")

    def fake_get(url, params, timeout):
        count = len(params["latitude"].split(","))
        place = {"current": {"time": now, "interval": 900, "precipitation": 2.0}}
        return httpx.Response(200, json=[place] * count, request=httpx.Request("GET", url))

    monkeypatch.setattr("app.weather.httpx.get", fake_get)
    assert client.post("/api/live/rainfall").json() == {"added": 6}
    assert client.post("/api/live/rainfall").json() == {"added": 0}
    (hyp,) = get(client, dataset="live")["hypotheses"]
    assert hyp["score"] == 0.7  # 2 mm in 15 min is 8 mm/h, above the threshold


def test_weather_outage_is_reported(client, monkeypatch):
    def down(*args, **kwargs):
        raise httpx.ConnectError("down")

    monkeypatch.setattr("app.weather.httpx.get", down)
    assert client.post("/api/live/rainfall").status_code == 502
