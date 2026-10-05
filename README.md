# healthConnector — read-only Intervals.icu MCP server

A **read-only** [Model Context Protocol](https://modelcontextprotocol.io) server that lets Claude (web, desktop and mobile) read your [Intervals.icu](https://intervals.icu) data through a custom connector: activities, wellness, events, training load, zones, power curves, workouts and plans.

Data path: **watch → Garmin Connect → Intervals.icu → this server → Claude.** The server talks only to the Intervals.icu API, using a personal API key. It never talks to Garmin directly.

This is a fork of [abamy/intervals-mcp-server](https://github.com/abamy/intervals-mcp-server) (imported at `6d2a7c2`), which is itself a fork of [mvilanova/intervals-mcp-server](https://github.com/mvilanova/intervals-mcp-server). It is licensed under GPL-3.0, like upstream.

## What this fork changes

- **No write tools.** The 22 tools that could create, edit or delete data on Intervals.icu are gone, along with their helpers and tests. That covers activities, intervals, events, workouts, custom items and training plans. 34 read tools remain ([list below](#tools)).
- **GET only.** The API client has no way to send any other HTTP method. IDs that tools put into URL paths are validated, so an argument like `../athlete/i999/wellness` can't reach a different endpoint or athlete.
- **Credentials only from the environment.** No tool accepts `api_key` or `athlete_id`. The server uses `API_KEY` and `ATHLETE_ID` from its environment and nothing else.
- **Enforced by tests.** [`tests/test_read_only.py`](tests/test_read_only.py) fails if a non-read-only tool, a write HTTP verb, a credential argument or a path-traversal hole comes back.
- **Pinned dependencies.** `fastmcp` and `mcp` are pinned to exact versions in `pyproject.toml`, because Prefect Horizon installs from `pyproject.toml` and ignores `uv.lock`.

## Prerequisites

1. **Intervals.icu API key.** In Intervals.icu go to **Settings**, then the **Developer Settings / API** section, and generate a key.
2. **Athlete ID.** The `iNNNNN` in the URL when you're logged in, e.g. `https://intervals.icu/athlete/i12345/...` gives `i12345`.
3. **Garmin wellness sync.** On the Garmin card in Intervals.icu **Settings**, make sure **Download wellness data** is ticked. Use **Download old data** to backfill history.

## Deploy on Prefect Horizon (formerly FastMCP Cloud)

Horizon hosts FastMCP servers from a GitHub repo. It has a free personal tier and puts an OAuth gateway in front of every server, so only you (your Horizon account) can connect.

1. Sign in at [horizon.prefect.io](https://horizon.prefect.io) with GitHub. When asked, install the Horizon GitHub app and grant it access to `MaxPatwardhan/healthConnector`.
2. Create a new server from that repo:
   - **Server name:** anything, e.g. `intervals`. It becomes the subdomain, `https://<server-name>.fastmcp.app`.
   - **Entrypoint:** `src/intervals_mcp_server/server.py:mcp`
   - **Requirements / dependency file:** leave blank. Dependencies come from `pyproject.toml`.
3. Under **Settings → Environment Variables**, add the following for **Production**. Both are stored as sensitive values.

   | Key | Value |
   |-----|-------|
   | `API_KEY` | Your Intervals.icu API key |
   | `ATHLETE_ID` | Your athlete ID, e.g. `i12345` |

   **Don't** set `MCP_CLIENT_ID`, `MCP_CLIENT_SECRET`, `MCP_SERVER_URL` or `MCP_TRANSPORT` on Horizon. Horizon's gateway already handles OAuth. Turning on this app's own OAuth as well creates a second auth layer, which shows up as a connector with no tools or as 403 / JSON-RPC `-32603` errors.
4. Deploy. Production builds track the repo's **default branch**: every push to it rebuilds the server. Your server URL is `https://<server-name>.fastmcp.app/mcp`.

If you change an environment variable, redeploy so it takes effect.

## Connect it to Claude

Connectors are account-wide, so one added on claude.ai also shows up in Claude Desktop and the mobile apps.

1. In Claude, open **Customize → Connectors** (older layouts: **Settings → Connectors**). Choose **Add → Add custom connector**.
2. **Name:** `intervals`. Don't put a dot in the name: connectors with a dot in their name have been reported to connect but expose no tools.
3. **URL:** `https://<server-name>.fastmcp.app/mcp`. It must end in `/mcp`.
4. Authentication:
   - **Horizon:** sign in with OAuth. If you're offered a choice of OAuth client, pick **Register automatically**. Leave client ID and secret empty. When the browser opens, log in with your **Horizon account**.
   - **Self-hosted** ([below](#self-hosting-in-a-container)): under **Advanced settings** (or **Use your own OAuth client**), enter your `MCP_CLIENT_ID` and `MCP_CLIENT_SECRET`.
5. In a chat, open **+ → Connectors** and turn on `intervals`. Every tool is read-only, so you can set its tool permissions to **Always allow**.

Then ask something like *"Show my wellness data for the last 14 days"*.

The Claude Free plan allows one custom connector. You can't change a connector's authentication settings after adding it; to change them, remove the connector and add it again.

## Self-hosting in a container

Use this if Horizon doesn't suit you. The included `Dockerfile` runs stdio by default, so set these variables on the container host:

| Key | Value |
|-----|-------|
| `API_KEY`, `ATHLETE_ID` | Your Intervals.icu credentials |
| `MCP_TRANSPORT` | `http` |
| `FASTMCP_HOST` | `0.0.0.0` |
| `FASTMCP_PORT` | The port the platform routes to (the server doesn't read `$PORT`) |
| `MCP_CLIENT_ID` | Any identifier, e.g. `intervals` |
| `MCP_CLIENT_SECRET` | A long random secret: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `MCP_SERVER_URL` | The public HTTPS base URL, **without** `/mcp`, e.g. `https://intervals.example.com` |

With `MCP_CLIENT_ID` and `MCP_CLIENT_SECRET` set, the server runs its own minimal OAuth server ([`auth.py`](src/intervals_mcp_server/auth.py)): authorization code + PKCE, auto-approved, one pre-registered client, no dynamic registration and no refresh tokens. It hands out the client secret as the bearer token. So **the secret is the key to your data**: keep it long and random, and rotate it by changing the variable and re-adding the connector.

Without those two variables, the HTTP endpoint is **unauthenticated**.

Run exactly one instance. Pending authorization codes live in memory.

## Tools

All 34 tools are annotated `readOnlyHint: true, destructiveHint: false`.

- **Wellness & training load:** `get_wellness_data`, `get_training_summary`, `get_athlete_zones`, `get_athlete_power_curves`
- **Activities:** `get_activities`, `get_activity_details`, `get_activity_intervals`, `get_activity_streams`, `get_activity_histogram`, `get_activity_messages`
- **Activity analysis:** `get_activity_curve`, `get_activity_best_efforts`, `get_activity_segments`, `get_activity_time_at_hr`, `get_activity_weather_summary`, `get_activity_interval_stats`, `get_activity_map`, `get_activity_power_vs_hr`, `get_activity_hr_load_model`, `get_activity_power_spike_model`
- **Activity search:** `search_activities`, `interval_search`, `get_activities_around`, `get_activities_by_ids`, `get_activity_tags`
- **Calendar:** `get_events`, `get_races`, `get_event_by_id`, `get_training_plan`
- **Workout library:** `get_workout_folders`, `list_workouts`, `get_workout`
- **Custom items:** `get_custom_items`, `get_custom_item_by_id`

The server also publishes a usage-guide resource, `intervals-icu://guide`.

### Wellness fields from Garmin

`get_wellness_data` returns whatever Intervals.icu holds for each day. With the Garmin sync, Intervals.icu imports resting HR, overnight HRV (rMSSD), sleep duration, sleep score and quality, weight, body fat, steps, VO2max and SpO2. SpO2 is often missing.

Garmin's **stress score is not imported**. The `stress` field is Intervals.icu's own subjective 1–4 rating. **Body Battery** only arrives if you have created the custom wellness fields `BodyBatteryMin` / `BodyBatteryMax`, and the tool shows custom fields only with `include_all_fields=True`. Training readiness, respiration and average sleeping HR don't come from Garmin.

## Local development

Requires Python 3.12+ and [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/MaxPatwardhan/healthConnector.git
cd healthConnector
uv sync --all-extras
cp .env.example .env    # then fill in API_KEY and ATHLETE_ID; .env is gitignored
```

Run checks (CI runs the same steps in [`.github/workflows/ci.yml`](.github/workflows/ci.yml)):

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src tests && uv run pytest
```

The tests are fully mocked and pin fake credentials. They never call Intervals.icu.

Run the server:

```bash
uv run python src/intervals_mcp_server/server.py                      # stdio (Claude Desktop)
MCP_TRANSPORT=http uv run python src/intervals_mcp_server/server.py   # http://127.0.0.1:8000/mcp
```

To use it locally from Claude Desktop, add an entry to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "intervals": {
      "command": "uv",
      "args": ["--directory", "/path/to/healthConnector", "run", "python", "src/intervals_mcp_server/server.py"]
    }
  }
}
```

The server picks up `API_KEY` and `ATHLETE_ID` from the `.env` file in the repo directory.

### Checking a running server

```bash
# Which wellness fields your account actually has, for the last 14 days (reads .env)
uv run python scripts/wellness_field_report.py 14

# List tools over HTTP, fail on anything mutating, and fetch 14 days of wellness
uv run python scripts/verify_server.py http://127.0.0.1:8000/mcp --days 14
```

For a Horizon deployment, put a Horizon API key (`fmcp_...`, created under your user menu → **API Keys**) in an environment variable and pass its name, for example `--token-env HORIZON_TOKEN`. Pass the variable's name, not the key itself; the script never prints the token.

## License

GPL-3.0. See [LICENSE](LICENSE). Original work by Marc Vilanova and contributors ([mvilanova/intervals-mcp-server](https://github.com/mvilanova/intervals-mcp-server)), with changes from [abamy/intervals-mcp-server](https://github.com/abamy/intervals-mcp-server).
