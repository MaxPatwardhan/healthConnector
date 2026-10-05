"""
Lightweight sanity tests for the activity analysis and search tools.

Verifies URL routing and query-parameter shape per the OpenAPI spec. Network calls are mocked via monkeypatching
``make_intervals_request`` on each tool module.
"""

import asyncio
import json
import os
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.tools.activity_analysis import (  # noqa: E402
    get_activity_best_efforts,
    get_activity_curve,
    get_activity_interval_stats,
    get_activity_map,
)
from intervals_mcp_server.tools.activity_search import (  # noqa: E402
    get_activities_around,
    get_activity_tags,
    interval_search,
    search_activities,
)


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


def _patch(monkeypatch, module_path: str, fake: FakeRequest) -> None:
    monkeypatch.setattr(f"intervals_mcp_server.tools.{module_path}.make_intervals_request", fake)


# ---------------------------------------------------------------------------
# Activity search
# ---------------------------------------------------------------------------


def test_search_activities_summary(monkeypatch):
    fake = FakeRequest(response=[])
    _patch(monkeypatch, "activity_search", fake)
    asyncio.run(search_activities("vo2", limit=5))
    assert fake.last["url"] == "/athlete/i1/activities/search"
    assert fake.last["params"] == {"q": "vo2", "limit": 5}


def test_search_activities_full_uses_search_full(monkeypatch):
    fake = FakeRequest(response=[])
    _patch(monkeypatch, "activity_search", fake)
    asyncio.run(search_activities("#race", full=True))
    assert fake.last["url"] == "/athlete/i1/activities/search-full"


def test_interval_search_sends_required_params(monkeypatch):
    fake = FakeRequest(response=[])
    _patch(monkeypatch, "activity_search", fake)
    asyncio.run(
        interval_search(
            min_secs=60,
            max_secs=300,
            min_intensity=95,
            max_intensity=120,
            min_reps=3,
        )
    )
    p = fake.last["params"]
    assert p["minSecs"] == 60
    assert p["maxSecs"] == 300
    assert p["minIntensity"] == 95
    assert p["maxIntensity"] == 120
    assert p["minReps"] == 3


def test_get_activities_around(monkeypatch):
    fake = FakeRequest(response=[])
    _patch(monkeypatch, "activity_search", fake)
    asyncio.run(get_activities_around("a1", limit=10))
    assert fake.last["url"] == "/athlete/i1/activities-around"
    assert fake.last["params"]["activity_id"] == "a1"
    assert fake.last["params"]["limit"] == 10


def test_get_activity_tags(monkeypatch):
    fake = FakeRequest(response=["climbing", "race"])
    _patch(monkeypatch, "activity_search", fake)
    result = asyncio.run(get_activity_tags())
    assert fake.last["url"] == "/athlete/i1/activity-tags"
    assert "climbing" in result


# ---------------------------------------------------------------------------
# Activity analysis
# ---------------------------------------------------------------------------


def test_get_activity_curve_hr(monkeypatch):
    fake = FakeRequest(response={"curve": []})
    _patch(monkeypatch, "activity_analysis", fake)
    asyncio.run(get_activity_curve("a1", curve_type="hr"))
    assert fake.last["url"] == "/activity/a1/hr-curve.json"


def test_get_activity_curve_pace_with_gap(monkeypatch):
    fake = FakeRequest(response={"curve": []})
    _patch(monkeypatch, "activity_analysis", fake)
    asyncio.run(get_activity_curve("a1", curve_type="pace", gap=True))
    assert fake.last["url"] == "/activity/a1/pace-curve.json"
    assert fake.last["params"] == {"gap": True}


def test_get_activity_curve_power_multi(monkeypatch):
    fake = FakeRequest(response={"curves": []})
    _patch(monkeypatch, "activity_analysis", fake)
    asyncio.run(
        get_activity_curve(
            "a1",
            curve_type="power-multi",
            streams="watts,watts_alt",
            fatigue="normal,kj1",
        )
    )
    assert fake.last["url"] == "/activity/a1/power-curves.json"
    assert fake.last["params"]["types"] == "watts,watts_alt"
    assert fake.last["params"]["fatigue"] == "normal,kj1"


def test_get_activity_curve_invalid_type():
    result = asyncio.run(get_activity_curve("a1", curve_type="bogus"))
    assert "Invalid curve_type" in result


def test_get_activity_best_efforts(monkeypatch):
    fake = FakeRequest(response=[])
    _patch(monkeypatch, "activity_analysis", fake)
    asyncio.run(
        get_activity_best_efforts(
            "a1", stream="watts", duration=300, count=5, exclude_intervals=True
        )
    )
    assert fake.last["url"] == "/activity/a1/best-efforts"
    p = fake.last["params"]
    assert p["stream"] == "watts"
    assert p["duration"] == 300
    assert p["count"] == 5
    assert p["excludeIntervals"] is True


def test_get_activity_interval_stats(monkeypatch):
    fake = FakeRequest(response={})
    _patch(monkeypatch, "activity_analysis", fake)
    asyncio.run(get_activity_interval_stats("a1", start_index=0, end_index=500))
    assert fake.last["url"] == "/activity/a1/interval-stats"
    assert fake.last["params"] == {"start_index": 0, "end_index": 500}


def test_get_activity_map(monkeypatch):
    fake = FakeRequest(response={})
    _patch(monkeypatch, "activity_analysis", fake)
    asyncio.run(get_activity_map("a1", bounds_only=True, weather=True))
    assert fake.last["url"] == "/activity/a1/map"
    assert fake.last["params"] == {"boundsOnly": True, "weather": True}


# ---------------------------------------------------------------------------
# Power curves fix verification (uses athlete tool, not module above)
# ---------------------------------------------------------------------------


def test_power_curves_sends_required_filters_and_json_ext(monkeypatch):
    from intervals_mcp_server.tools import power_curves as pc_mod

    fake = FakeRequest(response={"list": []})
    monkeypatch.setattr("intervals_mcp_server.tools.power_curves.make_intervals_request", fake)
    asyncio.run(pc_mod.get_athlete_power_curves(activity_type="Ride"))
    assert fake.last["url"] == "/athlete/i1/power-curves.json"
    p = fake.last["params"]
    assert p["f1"] == json.dumps([])
    assert p["f2"] == json.dumps([])
    assert p["f3"] == json.dumps([])


def test_activity_streams_uses_json_ext(monkeypatch):
    from intervals_mcp_server.tools import activities as act_mod

    fake = FakeRequest(response=[])
    monkeypatch.setattr("intervals_mcp_server.tools.activities.make_intervals_request", fake)
    asyncio.run(act_mod.get_activity_streams("a1"))
    assert fake.last["url"] == "/activity/a1/streams.json"
