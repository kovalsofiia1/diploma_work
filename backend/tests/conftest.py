import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.models import (  # noqa: F401
    admin_audit_log,
    checkin,
    email_verification,
    event,
    organizer_application,
    ticket,
    user,
)

# CI sets TEST_DATABASE_URL to a PostgreSQL database; locally tests default to
# an in-memory SQLite database so they run without any setup.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def make_test_engine():
    if TEST_DATABASE_URL:
        return create_engine(TEST_DATABASE_URL, future=True)
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )


@pytest.fixture()
def engine():
    engine = make_test_engine()
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


@pytest.fixture()
def db_session(session_factory):
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
