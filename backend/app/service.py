from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from . import demo, weather
from .config import settings
from .models import AlertDecision, Signal
from .reasoning import Hypothesis, Observation, SignalType, analyse
from .schemas import (
    AlertStatus,
    AnalysedSignal,
    AnalysisOut,
    Dataset,
    DecisionIn,
    EvidenceOut,
    HypothesisOut,
    SignalIn,
    SignalOut,
    Stats,
)

# shortcut: pairing is O(n^2) so only the newest signals are analysed, use PostGIS beyond this
MAX_SIGNALS = 500
REPORT_RAIN_LOOKBACK = timedelta(hours=1)


def _cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=settings.lookback_hours)


def run_analysis(
    session: Session, dataset: Dataset, radius_km: float, window_min: float
) -> AnalysisOut:
    signals = session.scalars(
        select(Signal)
        .where(Signal.dataset == dataset, Signal.observed_at >= _cutoff())
        .order_by(Signal.observed_at.desc(), Signal.id)
        .limit(MAX_SIGNALS)
    ).all()
    result = analyse(
        [
            Observation(s.id, SignalType(s.type), s.lat, s.lon, s.value, s.observed_at)
            for s in signals
        ],
        radius_km,
        window_min,
    )
    decisions = session.scalars(
        select(AlertDecision)
        .where(AlertDecision.dataset == dataset, AlertDecision.created_at >= _cutoff())
        .order_by(AlertDecision.id.desc())
    ).all()

    owner = {m.id: h.id for h in result.hypotheses for m in h.members}
    return AnalysisOut(
        radius_km=radius_km,
        window_min=window_min,
        stats=Stats(
            received=len(signals),
            aligned=len(owner),
            excluded=len(signals) - len(owner),
            aligned_pairs=sum(h.aligned_pairs for h in result.hypotheses),
        ),
        signals=[
            AnalysedSignal(
                **SignalOut.model_validate(s).model_dump(),
                hypothesis_id=owner.get(s.id),
                reason=result.reasons[s.id],
            )
            for s in signals
        ],
        hypotheses=[_to_out(h, decisions) for h in result.hypotheses],
    )


def _to_out(hyp: Hypothesis, decisions: Sequence[AlertDecision]) -> HypothesisOut:
    ids = {m.id for m in hyp.members}
    # Membership changes as signals arrive, so a decision follows its signals, not an event id
    latest = next((d for d in decisions if ids & set(d.signal_ids)), None)
    times = [m.observed_at for m in hyp.members]
    return HypothesisOut(
        id=hyp.id,
        title=hyp.title,
        score=hyp.score,
        lat=hyp.anchor.lat,
        lon=hyp.anchor.lon,
        started_at=min(times),
        ended_at=max(times),
        signal_ids=sorted(ids),
        aligned_pairs=hyp.aligned_pairs,
        evidence=[EvidenceOut(**vars(e)) for e in hyp.evidence],
        status=AlertStatus(latest.status) if latest else AlertStatus.NEW,
        new_signals=len(ids - set(latest.signal_ids)) if latest else 0,
    )


def add_signal(session: Session, data: SignalIn) -> Signal:
    signal = Signal(**data.model_dump())
    session.add(signal)
    session.commit()
    return signal


def record_decision(session: Session, data: DecisionIn) -> None:
    session.add(AlertDecision(**data.model_dump()))
    session.commit()


def load_demo(session: Session, scenario: demo.Scenario) -> int:
    """Replace the demo dataset only; live data is never touched."""
    session.execute(delete(AlertDecision).where(AlertDecision.dataset == Dataset.DEMO))
    session.execute(delete(Signal).where(Signal.dataset == Dataset.DEMO))
    signals = demo.build(scenario, datetime.now(timezone.utc))
    session.add_all(signals)
    session.commit()
    return len(signals)


def refresh_rainfall(session: Session) -> int:
    recent = session.execute(
        select(Signal.lat, Signal.lon)
        .where(
            Signal.dataset == Dataset.LIVE,
            Signal.type != SignalType.RAINFALL,
            Signal.observed_at >= datetime.now(timezone.utc) - REPORT_RAIN_LOOKBACK,
        )
        .order_by(Signal.observed_at.desc())
    ).all()
    points = weather.points_to_sample((lat, lon) for lat, lon in recent)
    rows = [
        {
            **reading,
            "dataset": Dataset.LIVE,
            "type": SignalType.RAINFALL,
            "source": "Open-Meteo weather model",
        }
        for reading in weather.fetch_rainfall(points)
    ]
    inserted = session.scalars(
        insert(Signal)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["dataset", "external_id"])
        .returning(Signal.id)
    ).all()
    session.commit()
    return len(inserted)
