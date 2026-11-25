from datetime import datetime, timedelta, timezone

import pytest

from app.reasoning import Observation, SignalType, analyse

R, T, I = SignalType.RAINFALL, SignalType.TRAFFIC, SignalType.INCIDENT
NOW = datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
KM = 1 / 111.195  # one kilometre in degrees of latitude


def obs(id, kind, km=0.0, minutes=0.0, value=50.0):
    return Observation(id, kind, 19 + km * KM, 72.8, value, NOW + timedelta(minutes=minutes))


def test_full_pattern_scores_095():
    (hyp,) = analyse([obs(1, R), obs(2, T), obs(3, I)], 1, 15).hypotheses
    assert hyp.score == 0.95
    assert hyp.title == "Possible weather-related traffic disruption"
    assert hyp.aligned_pairs == 3


@pytest.mark.parametrize(
    "kinds, score, title",
    [
        ((R, T), 0.75, "Possible weather-related traffic disruption"),
        ((R, I), 0.70, "Possible weather-related road incident"),
        ((T, I), 0.65, "Possible incident-related traffic disruption"),
    ],
)
def test_partial_patterns(kinds, score, title):
    (hyp,) = analyse([obs(i, k) for i, k in enumerate(kinds)], 1, 15).hypotheses
    assert (hyp.score, hyp.title) == (score, title)


def test_limits_are_configurable():
    far = [obs(1, R), obs(2, T, km=1.2)]
    assert not analyse(far, 1, 15).hypotheses
    assert analyse(far, 1.5, 15).hypotheses
    assert analyse([obs(1, R), obs(2, T, minutes=15)], 1, 15).hypotheses
    assert not analyse([obs(1, R), obs(2, T, minutes=16)], 1, 15).hypotheses


def test_one_signal_type_is_not_cross_signal():
    result = analyse([obs(1, R), obs(2, R)], 1, 15)
    assert not result.hypotheses
    assert "No other signal type" in result.reasons[1]


def test_weak_reading_is_not_evidence():
    result = analyse([obs(1, R, value=0.5), obs(2, T)], 1, 15)
    assert not result.hypotheses
    assert "below the evidence threshold" in result.reasons[1]


def test_chain_does_not_merge_into_one_event():
    chain = [obs(i, (R, T)[i % 2], km=i * 0.9) for i in range(6)]
    result = analyse(chain, 1, 15)
    assert len(result.hypotheses) == 2
    # each group's ends are 1.8 km apart, so one of its three pairs is not aligned
    assert all(h.aligned_pairs == 2 for h in result.hypotheses)
    assert result.hypotheses[0].evidence[3].points == pytest.approx(0.0667, abs=1e-4)


def test_anchor_is_the_most_central_signal():
    data = [obs(1, R), obs(2, T, km=0.4), obs(3, I, km=0.9)]
    assert analyse(data, 1, 15).hypotheses[0].anchor.id == 2


def test_exclusion_names_the_failed_limit():
    event = [obs(1, R), obs(2, T)]
    result = analyse(event + [obs(3, T, km=5), obs(4, T, minutes=60)], 1, 15)
    assert result.reasons[3] == "Nearest event: 5.0 km away (limit 1 km)"
    assert result.reasons[4] == "Nearest event: 60 min apart (limit 15 min)"


def test_order_does_not_change_the_result():
    data = [obs(1, R), obs(2, T, km=0.5), obs(3, I, km=0.9), obs(4, T, km=1.6)]
    assert analyse(data, 1, 15) == analyse(data[::-1], 1, 15)


def test_empty():
    assert analyse([], 1, 15).hypotheses == []
