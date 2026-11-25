from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (UniqueConstraint("dataset", "external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset: Mapped[str] = mapped_column(String(8), index=True)
    type: Mapped[str] = mapped_column(String(20))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    value: Mapped[float] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(300), default="")
    external_id: Mapped[str | None] = mapped_column(String(120))


class AlertDecision(Base):
    """One operator decision. The app only ever adds rows; a demo reset clears demo rows."""

    __tablename__ = "alert_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset: Mapped[str] = mapped_column(String(8), index=True)
    status: Mapped[str] = mapped_column(String(16))
    signal_ids: Mapped[list[int]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
