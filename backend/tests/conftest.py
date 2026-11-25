import os

import pytest

if not os.environ.get("TEST_DATABASE_URL"):
    import tempfile
    from pathlib import Path

    import pgserver

    _server = pgserver.get_server(Path(tempfile.mkdtemp(prefix="civicpulse-test-")))
    os.environ["TEST_DATABASE_URL"] = _server.get_uri()
# Set before the app is imported so tests can never touch the development database
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.database import Base, engine
    from app.main import app

    Base.metadata.drop_all(engine)
    with TestClient(app) as test_client:
        yield test_client
