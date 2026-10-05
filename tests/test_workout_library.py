"""
Unit tests for the workout library MCP tools.

These tests use monkeypatching to mock API responses and verify
formatting / output of each workout-library tool function:
- get_workout_folders
- list_workouts
- get_workout
"""

import asyncio
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")


def _get_tool(name: str):
    """Return the tool function from the current (possibly re-imported) workout_library module.

    test_server_config.py clears ``sys.modules`` and re-imports the server, so
    function references captured at import time may point to stale module
    globals. This helper always resolves through ``sys.modules`` so
    monkeypatching works regardless of test ordering.
    """
    mod = sys.modules.get("intervals_mcp_server.tools.workout_library")
    if mod is None:
        import intervals_mcp_server.tools.workout_library as mod
    return getattr(mod, name)


# Trigger initial import so the module is in sys.modules
import intervals_mcp_server.server  # noqa: E402, F401


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_FOLDER = {
    "id": 10,
    "name": "Sweet Spot Plans",
    "type": "PLAN",
    "num_workouts": 5,
    "visibility": "PRIVATE",
    "description": "Base building plans",
    "activity_types": ["Ride"],
    "athlete_id": "i1",
    "children": [{"id": 99, "name": "should be stripped"}],
}

SAMPLE_WORKOUT_A = {
    "id": 1,
    "name": "Tempo 2x20",
    "type": "Ride",
    "folder_id": 10,
    "moving_time": 3600,
    "icu_training_load": 80,
    "tags": ["tempo"],
    "description": "Two 20-minute tempo intervals",
    "distance": 40000,
    "indoor": True,
    "color": "#ff0000",
    "updated": "2025-06-01T12:00:00Z",
    "workout_doc": {"steps": [{"duration": 1200}]},
}

SAMPLE_WORKOUT_B = {
    "id": 2,
    "name": "Endurance",
    "type": "Ride",
    "folder_id": 20,
    "moving_time": 7200,
    "icu_training_load": 60,
    "tags": [],
    "workout_doc": {"steps": []},
}


SAMPLE_SHARED_FOLDER = {
    "id": 30,
    "name": "Coach Shared Plan",
    "type": "PLAN",
    "num_workouts": 2,
    "visibility": "PUBLIC",
    "description": "Shared by coach",
    "activity_types": ["Run"],
    "athlete_id": "i_coach",
    "children": [
        {
            "id": 100,
            "name": "Shared Tempo Run",
            "type": "Run",
            "folder_id": 30,
            "moving_time": 2400,
            "icu_training_load": 50,
            "tags": ["tempo"],
        },
        {
            "id": 101,
            "name": "Shared Easy Run",
            "type": "Run",
            "folder_id": 30,
            "moving_time": 3600,
            "icu_training_load": 30,
            "tags": [],
        },
    ],
}


def _patch_workout_lib(monkeypatch, fake_request):
    """Patch make_intervals_request in the current workout_library module (handles reloads)."""
    mod = sys.modules.get("intervals_mcp_server.tools.workout_library")
    if mod is None:
        import intervals_mcp_server.tools.workout_library as mod
    monkeypatch.setattr(mod, "make_intervals_request", fake_request)


# ---------------------------------------------------------------------------
# get_workout_folders
# ---------------------------------------------------------------------------


def test_get_workout_folders_success(monkeypatch):
    """Folders are returned with children stripped and shared flag."""

    async def fake_request(*_a, **_kw):
        return [SAMPLE_FOLDER, SAMPLE_SHARED_FOLDER]

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("get_workout_folders")())
    folders = json.loads(result)
    assert len(folders) == 2
    assert folders[0]["id"] == 10
    assert "children" not in folders[0]
    assert folders[0]["name"] == "Sweet Spot Plans"
    assert folders[0]["shared"] is False
    # Shared folder owned by a different athlete
    assert folders[1]["id"] == 30
    assert folders[1]["shared"] is True


def test_get_workout_folders_empty(monkeypatch):
    """Empty list returns a human-readable message."""

    async def fake_request(*_a, **_kw):
        return []

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("get_workout_folders")())
    assert "No workout folders found" in result


def test_get_workout_folders_error(monkeypatch):
    """API error returns an error message."""

    async def fake_request(*_a, **_kw):
        return {"error": True, "message": "Unauthorized"}

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("get_workout_folders")())
    assert "Error fetching workout folders" in result


# ---------------------------------------------------------------------------
# list_workouts
# ---------------------------------------------------------------------------


def test_list_workouts_compact(monkeypatch):
    """Compact mode returns only compact fields; workout_doc is never present."""

    async def fake_request(*_a, **_kw):
        return [SAMPLE_WORKOUT_A, SAMPLE_WORKOUT_B]

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("list_workouts")(compact=True))
    workouts = json.loads(result)
    assert len(workouts) == 2
    assert "workout_doc" not in workouts[0]
    assert workouts[0]["name"] == "Tempo 2x20"
    # Compact mode should not include full-mode extras
    assert "description" not in workouts[0]
    assert "distance" not in workouts[0]


def test_list_workouts_full(monkeypatch):
    """Full mode includes extra fields but still omits workout_doc."""

    async def fake_request(*_a, **_kw):
        return [SAMPLE_WORKOUT_A]

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("list_workouts")(compact=False))
    workouts = json.loads(result)
    assert workouts[0]["description"] == "Two 20-minute tempo intervals"
    assert "workout_doc" not in workouts[0]


def test_list_workouts_folder_filter(monkeypatch):
    """folder_id filters own workouts client-side."""

    async def fake_request(*_a, **kw):
        if "/workouts" in kw.get("url", ""):
            return [SAMPLE_WORKOUT_A, SAMPLE_WORKOUT_B]
        return []

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("list_workouts")(folder_id=10))
    workouts = json.loads(result)
    assert len(workouts) == 1
    assert workouts[0]["id"] == 1


def test_list_workouts_folder_filter_no_match(monkeypatch):
    """folder_id that matches nothing in either endpoint returns human message."""

    async def fake_request(*_a, **kw):
        url = kw.get("url", "")
        if "/workouts" in url:
            return [SAMPLE_WORKOUT_A]
        if "/folders" in url:
            return [SAMPLE_FOLDER]  # folder 10, no folder 999
        return []

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("list_workouts")(folder_id=999))
    assert "No workouts found" in result
    assert "folder 999" in result


def test_list_workouts_shared_folder_fallback(monkeypatch):
    """Shared folder workouts are returned with shared indicator."""

    async def fake_request(*_a, **kw):
        url = kw.get("url", "")
        if "/workouts" in url:
            return [SAMPLE_WORKOUT_A]  # own workouts, none in folder 30
        if "/folders" in url:
            return [SAMPLE_SHARED_FOLDER]  # shared folder 30 with children
        return []

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("list_workouts")(folder_id=30))
    data = json.loads(result)
    assert data["shared"] is True
    workouts = data["workouts"]
    assert len(workouts) == 2
    assert workouts[0]["name"] == "Shared Tempo Run"
    assert workouts[1]["name"] == "Shared Easy Run"


def test_list_workouts_error(monkeypatch):
    """API error is surfaced."""

    async def fake_request(*_a, **_kw):
        return {"error": True, "message": "Forbidden"}

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("list_workouts")())
    assert "Error fetching workouts" in result


def test_list_workouts_type_filter(monkeypatch):
    """workout_type filters workouts by activity type (case-insensitive)."""
    run_workout = {
        "id": 3,
        "name": "Easy Run",
        "type": "Run",
        "folder_id": 10,
        "moving_time": 2400,
        "icu_training_load": 40,
        "tags": ["easy"],
    }

    async def fake_request(*_a, **_kw):
        return [SAMPLE_WORKOUT_A, SAMPLE_WORKOUT_B, run_workout]

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("list_workouts")(workout_type="run"))
    workouts = json.loads(result)
    assert len(workouts) == 1
    assert workouts[0]["name"] == "Easy Run"


def test_list_workouts_type_filter_no_match(monkeypatch):
    """workout_type that matches nothing returns helpful message."""

    async def fake_request(*_a, **_kw):
        return [SAMPLE_WORKOUT_A, SAMPLE_WORKOUT_B]

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("list_workouts")(workout_type="Swim"))
    assert "No workouts found" in result
    assert "type 'Swim'" in result


# ---------------------------------------------------------------------------
# get_workout
# ---------------------------------------------------------------------------


def test_get_workout_success(monkeypatch):
    """Full workout detail is returned including workout_doc."""

    async def fake_request(*_a, **_kw):
        return SAMPLE_WORKOUT_A

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("get_workout")(workout_id=1))
    data = json.loads(result)
    assert data["id"] == 1
    assert "workout_doc" in data


def test_get_workout_not_found(monkeypatch):
    """Non-existent workout returns helpful message."""

    async def fake_request(*_a, **_kw):
        return {}

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("get_workout")(workout_id=999))
    assert "No workout found" in result


def test_get_workout_error(monkeypatch):
    """API error returns error message."""

    async def fake_request(*_a, **_kw):
        return {"error": True, "message": "Not Found"}

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("get_workout")(workout_id=1))
    assert "Error fetching workout" in result


def test_get_workout_folders_no_athlete(monkeypatch):
    """Without a configured ATHLETE_ID the tool errors before calling the API."""
    from intervals_mcp_server.config import get_config

    async def fake_request(*_a, **_kw):
        raise AssertionError("no request should be made without an athlete ID")

    monkeypatch.setattr(get_config(), "athlete_id", "")
    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("get_workout_folders")())
    assert "No athlete ID configured" in result
