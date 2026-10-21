"""Thin LLM client used by the chatbot.

The chatbot business logic only depends on the ``LLMClient`` protocol, so the
provider/model can be swapped through env vars (LLM_PROVIDER / LLM_MODEL) and
tests can inject a fake client instead of calling the network.
"""
import asyncio
import json
import logging
from functools import lru_cache
from typing import Any, Optional, Protocol

from any_llm import acompletion

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class LLMUnavailableError(Exception):
    """Provider failed, timed out or returned something unusable."""


class LLMBadOutputError(LLMUnavailableError):
    """The provider answered, but not with usable JSON (e.g. the model refused the request)."""


class LLMClient(Protocol):
    async def complete_json(self, system: str, user: str, *, max_tokens: Optional[int] = None) -> dict[str, Any]:
        """Run one chat completion and return the model's answer parsed as a JSON object."""
        ...


class AnyLLMClient:
    def __init__(self, *, provider: str, model: str, api_key: str = "", timeout_seconds: float = 4.0, max_tokens: int = 300, reasoning_effort: str = ""):
        self._provider = provider
        self._model = model
        self._api_key = api_key or None
        self._timeout = timeout_seconds
        self._max_tokens = max_tokens
        self._reasoning_effort = reasoning_effort or None

    async def complete_json(self, system: str, user: str, *, max_tokens: Optional[int] = None) -> dict[str, Any]:
        try:
            response = await asyncio.wait_for(
                acompletion(
                    model=self._model,
                    provider=self._provider,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=0,
                    max_tokens=max_tokens or self._max_tokens,
                    response_format={"type": "json_object"},
                    reasoning_effort=self._reasoning_effort,
                    api_key=self._api_key,
                ),
                timeout=self._timeout,
            )
            content = response.choices[0].message.content or ""
            data = json.loads(content)
        except asyncio.TimeoutError as exc:
            logger.warning("LLM call timed out after %.1fs", self._timeout)
            raise LLMUnavailableError("LLM request timed out") from exc
        except json.JSONDecodeError as exc:
            logger.warning("LLM returned invalid JSON")
            raise LLMBadOutputError("LLM returned invalid JSON") from exc
        except Exception as exc:  # provider SDKs raise many different error types (rate limit, auth, network)
            logger.warning("LLM call failed: %s", type(exc).__name__)
            if "json_validate_failed" in str(exc):  # Groq: model produced text instead of JSON, e.g. a refusal
                raise LLMBadOutputError("LLM could not produce JSON") from exc
            raise LLMUnavailableError("LLM provider error") from exc

        if not isinstance(data, dict):
            raise LLMBadOutputError("LLM returned a non-object JSON value")
        return data


@lru_cache
def get_llm_client() -> LLMClient:
    """FastAPI dependency; override it in tests with a fake client."""
    settings = get_settings()
    return AnyLLMClient(
        provider=settings.llm_provider,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
        max_tokens=settings.llm_max_tokens,
        reasoning_effort=settings.llm_reasoning_effort,
    )
