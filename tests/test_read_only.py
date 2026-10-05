"""
Guards for the read-only guarantee of this fork.

The server must never be able to create, modify or delete anything on
Intervals.icu, and credentials must come only from the environment. These tests
fail if a write tool, a non-GET request path, or a per-call credential override
is ever reintroduced.
"""

import ast
import asyncio
import inspect
import pathlib

import httpx
import pytest

from intervals_mcp_server import server
from intervals_mcp_server.api import client as api_client
from intervals_mcp_server.mcp_instance import mcp

SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "intervals_mcp_server"

READ_TOOLS = {
    "get_activities",
    "get_activity_details",
    "get_activity_histogram",
    "get_activity_intervals",
    "get_activity_messages",
    "get_activity_streams",
    "get_activity_best_efforts",
    "get_activity_curve",
    "get_activity_hr_load_model",
    "get_activity_interval_stats",
    "get_activity_map",
    "get_activity_power_spike_model",
    "get_activity_power_vs_hr",
    "get_activity_segments",
    "get_activity_time_at_hr",
    "get_activity_weather_summary",
    "get_activities_around",
    "get_activities_by_ids",
    "get_activity_tags",
    "interval_search",
    "search_activities",
    "get_event_by_id",
    "get_events",
    "get_races",
    "get_athlete_zones",
    "get_custom_item_by_id",
    "get_custom_items",
    "get_athlete_power_curves",
    "get_training_plan",
    "get_training_summary",
    "get_wellness_data",
    "get_workout",
    "get_workout_folders",
    "list_workouts",
}

WRITE_VERBS = {"POST", "PUT", "PATCH", "DELETE"}


def _tools():
    return asyncio.run(mcp.list_tools())


def test_registered_tools_are_exactly_the_read_tools():
    assert {t.name for t in _tools()} == READ_TOOLS


def test_every_tool_is_annotated_read_only_and_non_destructive():
    for tool in _tools():
        assert tool.annotations is not None, tool.name
        assert tool.annotations.read_only_hint is True, tool.name
        assert tool.annotations.destructive_hint is False, tool.name


@pytest.mark.parametrize("param", ["api_key", "athlete_id", "base_url", "url", "method"])
def test_no_tool_accepts_credential_or_routing_overrides(param):
    offenders = [t.name for t in _tools() if param in t.parameters.get("properties", {})]
    assert not offenders, f"{param!r} must not be a tool argument: {offenders}"


def test_make_intervals_request_has_no_method_body_or_key_parameters():
    params = set(inspect.signature(api_client.make_intervals_request).parameters)
    assert params == {"url", "params"}


def test_source_contains_no_write_http_verbs():
    """No string literal anywhere in the package names a write verb."""
    hits = []
    for path in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value.strip().upper() in WRITE_VERBS:
                    hits.append(f"{path.relative_to(SRC)}:{node.lineno} {node.value!r}")
    assert not hits, hits


def test_only_the_api_client_imports_an_http_library():
    http_libs = {"httpx", "requests", "urllib", "urllib3", "aiohttp", "http.client", "socket"}
    importers = set()
    for path in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                names = {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                names = {node.module or ""}
            else:
                continue
            if any(
                name == lib or name.startswith(lib + ".") for name in names for lib in http_libs
            ):
                importers.add(str(path.relative_to(SRC)))
    assert importers == {"api/client.py"}


class _RecordingClient:
    """Stands in for httpx.AsyncClient and records each request."""

    def __init__(self):
        self.is_closed = False
        self.requests = []

    async def request(self, **kwargs):
        self.requests.append(kwargs)
        return httpx.Response(200, json=[], request=httpx.Request(kwargs["method"], kwargs["url"]))


def test_requests_are_get_with_env_api_key(monkeypatch):
    recorder = _RecordingClient()
    monkeypatch.setattr(server, "httpx_client", recorder)

    asyncio.run(server.get_wellness_data(start_date="2026-01-01", end_date="2026-01-14"))

    assert len(recorder.requests) == 1
    sent = recorder.requests[0]
    assert sent["method"] == "GET"
    assert sent["url"] == "https://intervals.icu/api/v1/athlete/i1/wellness"
    assert sent["auth"]._auth_header == httpx.BasicAuth("API_KEY", "test")._auth_header


@pytest.mark.parametrize(
    "activity_id",
    [
        "../athlete/i999/wellness",
        "..",
        "i1/../../athlete/i999",
        "i1?oldest=2020-01-01",
        "i1#frag",
        "%2e%2e",
        "i1 2",
    ],
)
def test_ids_cannot_escape_their_endpoint(monkeypatch, activity_id):
    recorder = _RecordingClient()
    monkeypatch.setattr(server, "httpx_client", recorder)

    result = asyncio.run(server.get_activity_details(activity_id))

    assert recorder.requests == []
    assert "Invalid request path" in result


def test_valid_ids_are_accepted(monkeypatch):
    recorder = _RecordingClient()
    monkeypatch.setattr(server, "httpx_client", recorder)

    asyncio.run(server.get_activities_by_ids(["i123", "456"]))

    assert len(recorder.requests) == 1
    assert recorder.requests[0]["method"] == "GET"
