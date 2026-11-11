"""Tests for GET /health."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.main import app


def test_health_reports_ok_when_database_is_reachable(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}


def test_health_reports_503_when_database_is_unreachable(client):
    # Point this one request at a database address where nothing is listening.
    dead_engine = create_engine(
        "postgresql+psycopg://nobody:nothing@127.0.0.1:1/none",
        connect_args={"connect_timeout": 1},
    )
    DeadSession = sessionmaker(bind=dead_engine)

    def broken_db():
        db = DeadSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = broken_db

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unreachable"}


def test_cors_allows_the_vite_dev_server(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
