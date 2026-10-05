# Contributor Guide

This project is a Python 3.12 backend service built with FastMCP and httpx: a **read-only** MCP server for Intervals.icu. All source code lives under `src/intervals_mcp_server` (tools in `src/intervals_mcp_server/tools/`) and tests live under `tests`. See `CLAUDE.md` for the architecture and conventions.

## Read-Only Policy
- Every tool is read-only: annotate with `ToolAnnotations(read_only_hint=True, destructive_hint=False)`, return a string, and fetch data only through `make_intervals_request(url, params)`, which only sends GET.
- Never add tools that create, modify or delete data, non-GET requests, or HTTP calls outside `api/client.py`.
- Credentials come only from the `API_KEY` and `ATHLETE_ID` environment variables; tools must not accept `api_key` or `athlete_id` arguments.
- `tests/test_read_only.py` enforces this. A new read tool must also be added to its `READ_TOOLS` set; don't weaken the guards.

## Development Environment
- Use [uv](https://github.com/astral-sh/uv) to create and manage the virtual environment.
  - `uv venv --python 3.12`
  - `source .venv/bin/activate`
- Sync dependencies including dev extras with `uv sync --all-extras`.
- When editing or running the server manually use `uv run python src/intervals_mcp_server/server.py` (stdio), `MCP_TRANSPORT=http uv run python src/intervals_mcp_server/server.py` (HTTP), or `uv run fastmcp run src/intervals_mcp_server/server.py:mcp`.

## Testing Instructions
- Run unit tests with `uv run pytest` from the repository root. `tests/conftest.py` pins fake credentials, so no real API key is needed.
- Ensure linting passes with `uv run ruff check .` and formatting with `uv run ruff format --check .` (rules are configured in `pyproject.toml`).
- Run static type checks using `uv run mypy src tests`.
- All of these (`ruff`, `mypy`, and `pytest`) should succeed before committing. CI (`.github/workflows/ci.yml`) runs the same checks against the locked dependencies on every push and pull request.

## PR Instructions
- Use concise commit messages.
- Title pull requests using the format `[intervals-mcp-server] <brief description>`.
- Describe any manual testing steps performed and mention whether `pytest`, `ruff`, and `mypy` passed.

There is currently no frontend code in this repository. If a frontend is added in the future (for example with React or another framework), document how to run and test it within this file.
