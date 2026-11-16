from typing import Any, Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import checkin, event, ticket, user  # noqa: F401


class FakeLLMClient:
    """Stands in for the real LLM: returns queued answers and records every prompt it was given."""

    def __init__(self, *answers: Any):
        self._answers = list(answers)
        self.calls: list[tuple[str, str]] = []

    async def complete_json(self, system: str, user: str, *, max_tokens: Optional[int] = None) -> dict[str, Any]:
        self.calls.append((system, user))
        if not self._answers:
            raise AssertionError("FakeLLMClient has no answer queued for this call")
        answer = self._answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


@pytest.fixture()
def fake_llm():
    """Factory: fake_llm({...filters json...}, {...answer json...}) or pass an LLMUnavailableError instance to simulate a failure."""

    def make(*answers: Any) -> FakeLLMClient:
        return FakeLLMClient(*answers)

    return make


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        future=True,
    )
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
