from datetime import datetime, timedelta, timezone
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from .reasoning import SignalType


class Dataset(StrEnum):
    DEMO = "demo"
    LIVE = "live"


class AlertStatus(StrEnum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


# Accepted range per type: mm/h, % below normal speed, severity 1-5
VALUE_RANGES = {
    SignalType.RAINFALL: (0, 500),
    SignalType.TRAFFIC: (0, 100),
    SignalType.INCIDENT: (1, 5),
}
MAX_CLOCK_SKEW = timedelta(minutes=5)


class SignalIn(BaseModel):
    dataset: Dataset
    type: SignalType
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    value: float
    observed_at: AwareDatetime
    source: str = Field(default="Operator report", min_length=1, max_length=80)
    description: str = Field(default="", max_length=300)

    @model_validator(mode="after")
    def check_value_and_time(self):
        low, high = VALUE_RANGES[self.type]
        if not low <= self.value <= high:
            raise ValueError(f"{self.type} value must be between {low} and {high}")
        if self.observed_at > datetime.now(timezone.utc) + MAX_CLOCK_SKEW:
            raise ValueError("observed_at cannot be in the future")
        return self


class SignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: SignalType
    lat: float
    lon: float
    value: float
    observed_at: datetime
    source: str
    description: str


class AnalysedSignal(SignalOut):
    hypothesis_id: str | None
    reason: str


class EvidenceOut(BaseModel):
    factor: str
    weight: float
    points: float
    detail: str


class AssetOut(BaseModel):
    kind: str
    name: str
    distance_m: int
    lat: float
    lon: float


class PriorityOut(BaseModel):
    level: str
    value: float
    reasons: list[str]


class HypothesisOut(BaseModel):
    id: str
    title: str
    score: float
    lat: float
    lon: float
    started_at: datetime
    ended_at: datetime
    signal_ids: list[int]
    aligned_pairs: int
    evidence: list[EvidenceOut]
    assets: list[AssetOut]
    rain_anomaly: str | None
    priority: PriorityOut
    status: AlertStatus
    new_signals: int = Field(description="Signals added since the last operator decision")


class Stats(BaseModel):
    received: int
    aligned: int
    excluded: int
    aligned_pairs: int


class AnalysisOut(BaseModel):
    radius_km: float
    window_min: float
    stats: Stats
    signals: list[AnalysedSignal]
    hypotheses: list[HypothesisOut]


class DecisionIn(BaseModel):
    dataset: Dataset
    status: AlertStatus
    signal_ids: list[int] = Field(min_length=1, max_length=500)
