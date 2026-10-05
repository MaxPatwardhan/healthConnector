# CLAUDE.md — Intervals.icu MCP Server (read-only)

## Project Overview

This is a **read-only Model Context Protocol (MCP) server** that connects Claude and other MCP clients to the [Intervals.icu](https://intervals.icu) training platform API. It exposes MCP tools for reading athlete data: activities and their analysis, events, workouts, wellness metrics, training plans, and more. It cannot create, modify or delete anything on Intervals.icu.

This repo is a fork of `abamy/intervals-mcp-server`, itself a fork of `mvilanova/intervals-mcp-server` (GPL-3.0). Keep `LICENSE` and the upstream attribution intact.

- **Language**: Python 3.12+
- **Framework**: FastMCP (the standalone `fastmcp` package, not the `mcp` SDK's bundled `mcp.server.fastmcp.FastMCP` — required for Prefect Horizon deployment). `mcp` is still a direct dependency for the OAuth authorization-server protocol used by `auth.py`. Both are pinned exactly (`fastmcp==4.0.11`, `mcp==2.3.0`) because Horizon resolves dependencies from `pyproject.toml` and ignores `uv.lock`.
- **HTTP client**: `httpx` (async), used only in `api/client.py`
- **Package manager**: `uv`
- **Linter/formatter**: `ruff`
- **Type checker**: `mypy`
- **Test runner**: `pytest` + `pytest-asyncio` + `pytest-mock`

---

## Repository Layout

```
src/intervals_mcp_server/
server.py          # Entry point; imports & re-exports all tools and resources (`mcp` is the deploy entrypoint)
mcp_instance.py    # Shared FastMCP singleton (import this to register tools); enables auth.py when MCP_CLIENT_* set
server_setup.py    # Transport selection & server startup logic
config.py          # Config dataclass + singleton loaded from env vars
auth.py            # Single-client OAuth provider (self-hosted HTTP only)
api/
  client.py        # make_intervals_request() — all HTTP calls go here (GET only)
tools/
  __init__.py      # Imports every tool module; __all__ lists all 34 tools
  activities.py    # get_activities, get_activity_details, get_activity_intervals,
                   # get_activity_streams, get_activity_histogram, get_activity_messages
  activity_analysis.py # get_activity_curve, get_activity_best_efforts, get_activity_segments,
                   # get_activity_time_at_hr, get_activity_weather_summary,
                   # get_activity_interval_stats, get_activity_map, get_activity_power_vs_hr,
                   # get_activity_hr_load_model, get_activity_power_spike_model
  activity_search.py # search_activities, interval_search, get_activities_around,
                   # get_activities_by_ids, get_activity_tags
  events.py        # get_events, get_races, get_event_by_id
  wellness.py      # get_wellness_data
  athlete.py       # get_athlete_zones
  power_curves.py  # get_athlete_power_curves
  training_summary.py # get_training_summary
  training_plan.py # get_training_plan
  custom_items.py  # get_custom_items, get_custom_item_by_id
  workout_library.py  # get_workout_folders, list_workouts, get_workout
resources/
  guide.py         # intervals-icu://guide MCP resource — usage guide for LLMs
utils/
  formatting.py    # Data formatting helpers (format_activity_summary, etc.)
  validation.py    # Input validation (athlete ID, dates, activity type), resolve_* helpers
  dates.py         # Date range utilities
  types.py         # TransportAliases enum (MCP_TRANSPORT values)

tests/
conftest.py                    # Pins fake API_KEY/ATHLETE_ID before imports; resets config per test
test_read_only.py              # Read-only guarantee guards (see "Adding a New MCP Tool")
test_server.py                 # Main tool tests (monkeypatched API calls)
test_activity_tools.py         # Activity analysis/search routing tests
test_activities_date_filter.py # Date filter logic tests
test_formatting.py             # Formatting utility tests
test_make_intervals_request.py # API client tests
test_training_summary.py       # Training summary tests
test_training_plan.py          # Training plan tool tests
test_validation.py             # Validation function tests
test_workout_library.py        # Workout library tool tests
test_guide_resource.py         # MCP resource tests
test_tool_annotations.py       # Tool annotation tests
test_server_config.py          # Server config tests
test_auth.py                   # OAuth provider tests
sample_data.py                 # Shared mock data for tests
ressources/                    # Static test fixtures (JSON, text files)
```

---

## Development Environment

```bash
# Create and activate the virtual environment
uv venv --python 3.12
source .venv/bin/activate

# Install all dependencies including dev extras
uv sync --all-extras

# Copy env template and fill in your credentials
cp .env.example .env
# Edit .env: set API_KEY and ATHLETE_ID
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `API_KEY` | Yes | Your Intervals.icu API key |
| `ATHLETE_ID` | Yes | Your athlete ID: digits (e.g. `123456`) or `i`-prefixed (e.g. `i123456`) |
| `INTERVALS_API_BASE_URL` | No | Defaults to `https://intervals.icu/api/v1` |
| `MCP_TRANSPORT` | No | `stdio` (default), `sse`, `http`, or `streamable-http` (`sse`/`http` are served as Streamable HTTP) |
| `FASTMCP_HOST` | No | Bind host for HTTP transport (default `127.0.0.1`; use `0.0.0.0` in a container) |
| `FASTMCP_PORT` | No | Port for HTTP transport (default `8000`) |
| `MCP_CLIENT_ID` | No | Self-host only. OAuth client ID. Must match what is entered in Claude.ai's connector settings. |
| `MCP_CLIENT_SECRET` | No | Self-host only. OAuth client secret / access token. Must match what is entered in Claude.ai's connector settings. |
| `MCP_SERVER_URL` | No | Self-host only. Public HTTPS URL of this server, without `/mcp` (default `http://localhost:8000`). Required for OAuth discovery when `MCP_CLIENT_ID`/`MCP_CLIENT_SECRET` are set. |

Credentials come **only** from the environment (or `.env`): no tool accepts `api_key` or `athlete_id` arguments, so every request uses `API_KEY`. Athlete-scoped tools (`/athlete/{id}/...`) always target `ATHLETE_ID`; activity-ID tools (`/activity/{id}/...`) can read any activity the API key can see.

When `MCP_CLIENT_ID` and `MCP_CLIENT_SECRET` are both set the server enables OAuth 2.0 authorization code + PKCE protection on all HTTP endpoints. FastMCP publishes `/.well-known/oauth-authorization-server` so Claude.ai can auto-discover the token endpoint. stdio transport is unaffected. Never set these on Prefect Horizon (see Operational Notes).

---

## Running the Server

```bash
# stdio transport (default)
uv run python src/intervals_mcp_server/server.py

# Streamable HTTP on http://127.0.0.1:8000/mcp
MCP_TRANSPORT=http uv run python src/intervals_mcp_server/server.py

# Via the fastmcp CLI, using the same entrypoint Horizon deploys
uv run fastmcp run src/intervals_mcp_server/server.py:mcp
```

`server.py` disables fastmcp's startup banner (it checks PyPI for a newer release) so Intervals.icu is the only outbound host; pass `--no-banner` to `fastmcp run` for the same effect.

### Docker

```bash
docker build -t intervals-mcp-server .
docker run -e API_KEY=... -e ATHLETE_ID=... intervals-mcp-server
```

---

## Code Quality — Required Before Every Commit

All four checks must pass:

```bash
uv run ruff check .            # Linting (auto-fix available with --fix)
uv run ruff format --check .   # Formatting (drop --check to apply)
uv run mypy src tests          # Static type checking
uv run pytest                  # Unit tests
```

CI (`.github/workflows/ci.yml`) runs `uv sync --locked --all-extras` and then exactly these four on every push and pull request. The tests are fully mocked and need no real credentials.

Pre-commit hooks (`.pre-commit-config.yaml`) enforce ruff lint, ruff format, typo checking, and run pytest on `git push`. Install them with:

```bash
pip install pre-commit
pre-commit install && pre-commit install -t pre-push
```

---

## Key Architectural Patterns

### Tool Registration

Tools register themselves automatically via `@mcp.tool()` decorators when the module is imported. Each tool module imports the shared `mcp` singleton from `mcp_instance.py`:

```python
from mcp.types import ToolAnnotations

from intervals_mcp_server.mcp_instance import mcp

@mcp.tool(annotations=ToolAnnotations(title="...", read_only_hint=True, destructive_hint=False))
async def my_tool(...) -> str:
  ...
```

`tools/__init__.py` imports all tool modules to trigger registration; `server.py` imports from it and re-exports the functions in `__all__` for test compatibility.

### All API Calls via `make_intervals_request()`

Every call to the Intervals.icu API goes through `api/client.py:make_intervals_request(url, params=None)`. Never use `httpx` (or any other HTTP library) in tool modules.

```python
result = await make_intervals_request(
    url=f"/athlete/{athlete_id}/activities",
    params={"oldest": start_date, "newest": end_date},
)
```

It only ever sends `GET` (`_READ_ONLY_METHOD`) with HTTP Basic auth from `API_KEY`; there is no `method`, `data` or `api_key` parameter. It rejects request paths containing anything other than `/`-separated segments of letters, digits, `-`, `_`, `.` and `,`, and rejects `.`/`..` segments, so IDs spliced into the URL cannot climb out of the resource they name (e.g. `../athlete/i999/wellness` is rejected).

Error responses always return `{"error": True, "message": "..."}` (plus `status_code` for HTTP errors). Always check before using the result:

```python
if isinstance(result, dict) and "error" in result:
    return f"Error: {result.get('message', 'Unknown error')}"
```

### Configuration Singleton

Config is loaded once and cached in `config.py`:

```python
from intervals_mcp_server.config import get_config

config = get_config()
athlete_id, error_msg = resolve_athlete_id(config.athlete_id)  # error if ATHLETE_ID is unset
```

---

## Adding a New MCP Tool

Only read tools may be added.

1. Create the function in the appropriate module under `src/intervals_mcp_server/tools/` (or create a new module and import it in `tools/__init__.py`).
2. Decorate with `@mcp.tool(annotations=ToolAnnotations(title="...", read_only_hint=True, destructive_hint=False))` — i.e. `readOnlyHint=True`, `destructiveHint=False`.
3. Use `resolve_athlete_id(config.athlete_id)` and `resolve_date_params()` from `utils/validation.py` for standard parameter handling. Never add `api_key` or `athlete_id` parameters; credentials come only from the environment.
4. Call `make_intervals_request(url, params)` for all API communication (GET only).
5. Return a formatted string (tools return `str`).
6. Re-export the function in `tools/__init__.py` and `server.py` (`__all__` lists), and add its name to `READ_TOOLS` in `tests/test_read_only.py`.
7. Write tests in `tests/` — mock the HTTP client, test both success and error paths.

**Never add write tools or non-GET requests.** No tool may create, modify or delete data on Intervals.icu, and `make_intervals_request` must stay GET-only with no method/body/key parameters. `tests/test_read_only.py` enforces this (exact tool set, read-only annotations, no `api_key`/`athlete_id`/`url`/`method` tool arguments, no write HTTP verbs in `src/`, exactly one HTTP call site in `src/` (`client.request(method=_READ_ONLY_METHOD)` in `api/client.py`), only `api/client.py` imports an HTTP library or the shared client, every tool called with a recording client sends only GET, requests use the env key, path traversal rejected). Do not weaken those tests to make a change pass.

---

## Testing Conventions

- All tool functions are `async`; tests use `@pytest.mark.asyncio` or `asyncio.run(...)`.
- Mock HTTP by monkeypatching `make_intervals_request` in the tool module that imported it, or by setting `intervals_mcp_server.server.httpx_client` to a fake client:
```python
async def fake_request(*_args, **_kwargs):
    return mock_data


monkeypatch.setattr("intervals_mcp_server.tools.activities.make_intervals_request", fake_request)
```
- `tests/conftest.py` sets `API_KEY=test` and `ATHLETE_ID=i1` before any server import and resets the config singleton for every test (autouse fixture), so a local `.env` never leaks in and URLs like `/athlete/i1/...` are stable. The `os.environ.setdefault(...)` lines at the top of older test files are redundant; new test files don't need them.
- Shared realistic mock data lives in `tests/sample_data.py`.
- Test files are named `test_*.py`; test functions are named `test_*`.

---

## PR / Commit Conventions

- Commit messages: concise, imperative (`Add get_races tool`, `Fix date filter edge case`).
- PR title format: `[intervals-mcp-server] <brief description>`.
- PR description should mention whether `ruff`, `mypy`, and `pytest` passed, and any manual testing steps.
- Direct commits to `main` are blocked by pre-commit hook.

---

## MCP Resource

The server exposes one MCP resource at `intervals-icu://guide` (registered in `resources/guide.py`). It returns a plain-text usage guide describing key concepts (Activities vs Events vs Wellness), metric definitions (CTL, ATL, TSB), and recommended tool call sequences for common coaching workflows. LLM clients should load this resource at the start of coaching conversations.

## Operational Notes / Gotchas

### OAuth / HTTP transport
Activates only when `MCP_CLIENT_ID` + `MCP_CLIENT_SECRET` are set (`auth.py`, `mcp_instance.py`), and is for self-hosting only. `SingleClientOAuthProvider` is deliberately minimal: auth code + PKCE, auto-approve (no login screen), no dynamic client registration, no refresh tokens; the client secret is issued as the bearer token. It subclasses `fastmcp.server.auth.OAuthProvider`, which itself subclasses `mcp.server.auth.provider.OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]` (all from `mcp.server.auth.provider`/`fastmcp.server.auth`, fixed generic params — do not
swap in ad hoc dataclasses for those three types or mypy's LSP check fails). Gotchas: IDs/secret must match the connector exactly (case-sensitive) and the connector URL must end in `/mcp`; `resource_base_url` must be set on the provider
(RFC 9728 metadata); the client must set `token_endpoint_auth_method="client_secret_post"` (mcp >= 1.23 defaults to None → 401 "Unsupported auth method"); `validate_scope` accepts empty scope. `fastmcp` and `mcp` are pinned to exact versions, so
re-run the tests and the OAuth flow end-to-end before bumping either (and commit the updated `uv.lock` alongside). Authorization codes live in memory, so run exactly one instance and verify the full connector OAuth flow manually after any redeploy.

### Prefect Horizon (formerly FastMCP Cloud)
Deploy at https://horizon.prefect.io with entrypoint `src/intervals_mcp_server/server.py:mcp`; production deploys come from the repo's default branch. Set only `API_KEY` and `ATHLETE_ID` there. Confirmed by hands-on testing, not just docs — Horizon puts its own OAuth gateway (dashboard: Server → Access → Authentication → "Horizon Authentication") in front of every deployment, and it **cannot be disabled on the free tier** (requires a paid plan). That gateway serves `/oauth2/authorize`, `/oauth2/token`, `/oauth2/register` and fully supersedes this app's `/authorize`/`/token` routes, so **do not set `MCP_CLIENT_ID`/`MCP_CLIENT_SECRET`/`MCP_SERVER_URL`/`MCP_TRANSPORT` on Horizon** — the app's provider stacked behind the gateway causes 403s. The server URL is `https://<server-name>.fastmcp.app/mcp`. In Claude, add a connector named `intervals` (no dot) with that URL (ending `/mcp`), leave the OAuth client to register automatically (DCR against Horizon's `registration_endpoint`), and log in with the Horizon account.

### Self-hosting (container)
With no gateway in front, the app's own OAuth applies. Set `MCP_TRANSPORT=http`, `FASTMCP_HOST=0.0.0.0`, `FASTMCP_PORT=<platform port>`, `MCP_CLIENT_ID=<any id>`, `MCP_CLIENT_SECRET=<long random>` (e.g. `python -c "import secrets;print(secrets.token_urlsafe(48))"`) and `MCP_SERVER_URL=https://<public host>` (no `/mcp`), plus `API_KEY`/`ATHLETE_ID`. The connector then uses `<MCP_SERVER_URL>/mcp` with that client ID and secret. Run exactly one instance.
