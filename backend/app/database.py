from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import NullPool

from .config import settings


class Base(DeclarativeBase):
    pass


def _resolve_url() -> str:
    url = settings.database_url
    if not url:
        if settings.vercel:
            raise RuntimeError("DATABASE_URL is not set for this Vercel deployment")
        from .dev_db import ensure_running  # needs a dev-only dependency

        url = ensure_running()
    return url.replace("postgres://", "postgresql://", 1).replace(
        "postgresql://", "postgresql+psycopg://", 1
    )


# Serverless instances share a hosted pooler, which does not support prepared statements
engine = create_engine(
    _resolve_url(),
    connect_args={"prepare_threshold": None},
    **({"poolclass": NullPool} if settings.vercel else {"pool_pre_ping": True}),
)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
