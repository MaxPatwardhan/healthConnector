"""
Lightweight sanity tests for the training-plan tool.

Verifies URL routing per the OpenAPI spec. Network calls are mocked via monkeypatching
``make_intervals_request`` on the training_plan module.
"""

import asyncio
import os
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.tools.training_plan import get_training_plan  # noqa: E402


class FakeRequest:
    """Records every call and returns a configurable response."""

    def __init__(self, response: Any = None):
        self.calls: list[dict[str, Any]] = []
        self.response: Any = response if response is not None else {"id": 1}

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self.response

    @property
    def last(self) -> dict[str, Any]:
        return self.calls[-1]


def _patch(monkeypatch, fake: FakeRequest) -> None:
    monkeypatch.setattr("intervals_mcp_server.tools.training_plan.make_intervals_request", fake)


def test_get_training_plan(monkeypatch):
    fake = FakeRequest(response={"training_plan_id": 42})
    _patch(monkeypatch, fake)
    result = asyncio.run(get_training_plan())
    assert fake.last["url"] == "/athlete/i1/training-plan"
    assert "42" in result
