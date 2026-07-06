"""
Shared pytest fixtures for the stock_platform backend test-suite.

The production app talks to PostgreSQL, but the tests run against an
in-memory SQLite database so they are fast and require no external
services. A single shared in-memory connection (StaticPool) is used so
every session in a test sees the same tables and rows.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.stocks import models  # noqa: F401  (registers models on Base)
from app.stocks.router import router as stock_router
from app.auth.router import router as auth_router, get_current_user


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(engine):
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def app(db_session):
    """A minimal FastAPI app wiring only the routers under test.

    We intentionally do NOT import app.main, because importing it triggers
    Base.metadata.create_all against the real PostgreSQL engine and starts
    the APScheduler background job.
    """
    application = FastAPI()
    application.include_router(stock_router, prefix="/api/stocks", tags=["stocks"])
    application.include_router(auth_router)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    application.dependency_overrides[get_db] = override_get_db
    return application


@pytest.fixture()
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def make_user(db_session):
    """Factory creating a persisted User with a hashed password."""
    from app.core.security import get_password_hash

    def _make(username="tester", password="secret123", cash_balance=10_000_000.0):
        user = models.User(
            username=username,
            hashed_password=get_password_hash(password),
            cash_balance=cash_balance,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


@pytest.fixture()
def auth_client(app, make_user):
    """A TestClient whose requests are authenticated as a fixed test user.

    get_current_user is overridden so endpoint tests can focus on business
    logic without exercising the full JWT flow (which is covered separately
    in test_auth_router.py).
    """
    user = make_user()

    def override_current_user():
        return user

    app.dependency_overrides[get_current_user] = override_current_user
    with TestClient(app) as c:
        c.test_user = user
        yield c
