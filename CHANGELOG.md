# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- OAuth 2.0 (authorization code + PKCE) for the HTTP transport. Optional; activates
  only when `MCP_CLIENT_ID` and `MCP_CLIENT_SECRET` are set (`MCP_SERVER_URL` required
  for discovery). stdio transport is unaffected.
- `"gap"` (gradient-adjusted pace) histogram type for `get_activity_histogram`.
- Activity analysis tools: `get_activity_curve`, `get_activity_best_efforts`,
  `get_activity_segments`, `get_activity_interval_stats`, `get_activity_map`,
  `get_activity_power_vs_hr`, `get_activity_hr_load_model`,
  `get_activity_power_spike_model`, `get_activity_time_at_hr`,
  `get_activity_weather_summary`.
- Activity search tools: `search_activities`, `interval_search`,
  `get_activities_around`, `get_activities_by_ids`, `get_activity_tags`.
- Training plan tool: `get_training_plan`.
- `tests/test_read_only.py`: guard tests for the read-only guarantee (exact tool set,
  read-only annotations, no credential parameters, no write verbs in tool source, only
  `api/client.py` imports an HTTP library, requests are GET with the environment API
  key, path traversal is rejected).
- `tests/conftest.py`: sets test `API_KEY`/`ATHLETE_ID` before imports and resets the
  config singleton for every test.

### Changed

- The server is read-only: it can read Intervals.icu data but cannot create, modify or
  delete anything. 34 read tools remain.
- Credentials come only from the environment (`API_KEY`, `ATHLETE_ID`); no tool accepts
  them as arguments. `resolve_athlete_id` takes only the configured value.
- The API client (`make_intervals_request(url, params=None)`) only sends GET and
  rejects request paths containing anything but letters, digits, `-`, `_`, `.`, `,`
  and `/`, or containing `.`/`..` segments, so IDs interpolated into URLs cannot reach
  other endpoints or athletes.
- `fastmcp` and `mcp` pinned exactly (`fastmcp==4.0.11`, `mcp==2.3.0`) because Prefect
  Horizon (formerly FastMCP Cloud) resolves dependencies from `pyproject.toml` and
  ignores `uv.lock`; `uv.lock` updated to match.
- fastmcp startup banner disabled (`show_banner=False`). It performs a PyPI version
  check, so Intervals.icu is now the only outbound host when run via `server.py`.
- Usage guide resource describes the server as read-only and lists only read tools.
- CI replaced by `.github/workflows/ci.yml`: `uv sync --locked --all-extras`,
  `ruff check`, `ruff format --check`, `mypy src tests` and `pytest` on every push and
  pull request.

### Removed

- All 22 write/delete tools:
  - activities: `add_activity_message`, `update_activity`, `delete_activity`,
    `create_manual_activity`, `bulk_create_manual_activities`;
  - activity intervals: `update_activity_intervals`, `update_activity_interval`,
    `delete_activity_intervals`, `split_activity_interval` (whole
    `tools/activity_intervals.py` module);
  - events: `add_or_update_event`, `delete_event`, `delete_events_by_date_range`;
  - custom items: `create_custom_item`, `update_custom_item`, `delete_custom_item`;
  - training plans: `change_training_plan`, `apply_plan_changes`,
    `apply_plan_to_calendar`, `change_athlete_plans_bulk`;
  - workouts: `create_workout`, `update_workout`, `schedule_workout`.
- `api_key` and `athlete_id` tool arguments.
- Workout DSL types (`WorkoutDoc`, `Step`, `Value`, `SportSettings` and their enums)
  from `utils/types.py`; only `TransportAliases` remains.
- `format_workout` and unused date helpers (`get_default_start_date`,
  `get_default_end_date`, `get_default_future_end_date`).
- Workflows: `pylint.yml` (never passed), `python-app.yml` (replaced by `ci.yml`),
  `stale.yml`, and `funding.yml`.

### Fixed

- OAuth token exchange on mcp >= 1.23 (set `token_endpoint_auth_method`), protected
  resource metadata (RFC 9728), and acceptance of an empty `scope=` from clients.

## [0.1.0] - 2025-06-01

### Added

- Initial release of Intervals.icu MCP Server.
- Activity tools: `get_activities`, `get_activity_details`, `get_activity_intervals`,
  `get_activity_streams`, `get_activity_histogram`, `get_activity_messages`,
  `add_activity_message`.
- Event tools: `get_events`, `get_event_by_id`, `add_or_update_event`, `delete_event`,
  `delete_events_by_date_range`.
- Wellness & training tools: `get_wellness_data`, `get_training_summary`,
  `get_athlete_power_curves`, `get_athlete_zones`.
- Custom-item tools: `get_custom_items`, `get_custom_item_by_id`, `create_custom_item`,
  `update_custom_item`, `delete_custom_item`.
- Docker support with Render deployment guide.
- Local setup via `uv` and `mcp` CLI.
