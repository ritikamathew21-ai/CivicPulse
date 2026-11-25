import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import service
from .database import Base, engine, get_session
from .demo import Scenario
from .schemas import AnalysisOut, Dataset, DecisionIn, SignalIn, SignalOut

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="CivicPulse API", lifespan=lifespan)
Db = Annotated[Session, Depends(get_session)]


@app.get("/api/health")
def health(db: Db) -> dict[str, str]:
    db.execute(text("select 1"))
    return {"status": "ok"}


@app.get("/api/analysis")
def analysis(
    db: Db,
    dataset: Dataset = Dataset.DEMO,
    radius_km: Annotated[float, Query(ge=0.1, le=10)] = 1.0,
    window_min: Annotated[float, Query(ge=1, le=120)] = 15.0,
) -> AnalysisOut:
    return service.run_analysis(db, dataset, radius_km, window_min)


@app.post("/api/signals", status_code=201)
def create_signal(data: SignalIn, db: Db) -> SignalOut:
    return SignalOut.model_validate(service.add_signal(db, data))


@app.post("/api/decisions", status_code=201)
def create_decision(data: DecisionIn, db: Db) -> dict[str, str]:
    service.record_decision(db, data)
    return {"status": data.status}


@app.post("/api/demo/{scenario}")
def load_demo(scenario: Scenario, db: Db) -> dict[str, int]:
    return {"loaded": service.load_demo(db, scenario)}


@app.post("/api/live/rainfall")
def refresh_rainfall(db: Db) -> dict[str, int]:
    try:
        return {"added": service.refresh_rainfall(db)}
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        logger.exception("Open-Meteo refresh failed")
        raise HTTPException(502, "Weather service is unavailable right now") from exc
