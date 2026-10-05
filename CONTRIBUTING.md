# Contributing to Intervals.icu MCP Server

Thank you for taking the time to contribute! This project is a **read-only** MCP server for Intervals.icu. It uses **Python 3.12** and manages its dependencies with [uv](https://github.com/astral-sh/uv). The following guide summarizes how to set up your environment and outlines the workflow we expect for pull requests.

## Read-only policy

This server must never be able to create, modify or delete anything on Intervals.icu. Contributions must keep it that way:

* Only read tools, annotated `read_only_hint=True` / `destructive_hint=False`.
* All API access goes through `make_intervals_request(url, params)` in `api/client.py`, which only sends GET. No other module may make HTTP calls.
* Credentials come only from the `API_KEY` and `ATHLETE_ID` environment variables; no tool takes `api_key` or `athlete_id` arguments.

Pull requests that add write tools or non-GET requests will not be accepted. `tests/test_read_only.py` enforces these rules; when you add a read tool, add its name to `READ_TOOLS` there.

## Development environment

1. Create a virtual environment and activate it:
   ```bash
   uv venv --python 3.12
   source .venv/bin/activate
   ```
2. Install all dependencies (including development extras):
   ```bash
   uv sync --all-extras
   ```
3. When working on or manually running the server, use:
   ```bash
   uv run python src/intervals_mcp_server/server.py                    # stdio
   MCP_TRANSPORT=http uv run python src/intervals_mcp_server/server.py # HTTP on :8000/mcp
   uv run fastmcp run src/intervals_mcp_server/server.py:mcp           # fastmcp CLI
   ```

## Dependency changes

1. Edit `pyproject.toml`.
2. Run `uv lock` (or `uv sync`).
3. Commit **both** `pyproject.toml` and `uv.lock` in the same commit.

If you add, remove, or relax a dependency but forget to update the lock file, CI will fail. Treat `uv.lock` as a first-class artifact: review it when it changes, but don’t fear committing it.

`fastmcp` and `mcp` are pinned to exact versions in `pyproject.toml` because Prefect Horizon installs from `pyproject.toml` and ignores `uv.lock`. Bump them deliberately, after re-running the tests and the OAuth flow.

## Code-only changes

For changes that do not modify dependencies, keep the lock file untouched. Run your tests with:

```bash
uv run --locked pytest
```

CI installs with `uv sync --locked`, which fails if `uv.lock` is out of sync with `pyproject.toml`. To check this locally, run `uv lock --check`.

## Why keep the lock file?

* **Reproducibility** – All collaborators and CI runners install identical hashes.
* **Security** – Hash pinning in `uv.lock` helps prevent supply-chain attacks.
* **Speed** – `uv` skips resolution when the lock matches, keeping installs lightning-fast.

Automated dependency upgrades are encouraged. You can use Dependabot, Renovate, or a scheduled GitHub Action that runs `uv lock --upgrade && git push` to keep the file fresh and generate tidy PRs. (The exact `fastmcp`/`mcp` pins only move when `pyproject.toml` is edited.)

## Testing

Before opening a pull request, ensure all checks pass locally:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run --locked pytest
```

CI (`.github/workflows/ci.yml`) runs `uv sync --locked --all-extras` followed by these same checks on every push and pull request. The tests are fully mocked: `tests/conftest.py` pins fake credentials, so no Intervals.icu API key is needed.

## Changelog and versioning

This project keeps a `CHANGELOG.md` in the repository root, formatted according to [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Version numbers follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (`MAJOR.MINOR.PATCH`).

### When to update the changelog

Every pull request that changes user-facing behaviour **must** add an entry under the `[Unreleased]` section of `CHANGELOG.md`. Group entries using the standard headings:

* **Added** — new features or tools.
* **Changed** — changes to existing functionality.
* **Deprecated** — features that will be removed in the future.
* **Removed** — features that have been removed.
* **Fixed** — bug fixes.
* **Security** — vulnerability patches.

Documentation-only or CI-only changes do not require a changelog entry.

### When to increment the version number

Version bumps happen at **release time**, not in every PR. When preparing a release:

1. Move everything under `[Unreleased]` into a new `[X.Y.Z] - YYYY-MM-DD` section.
2. Update the `version` field in `pyproject.toml` to match.
3. Commit both changes together with a message like `Release vX.Y.Z`.

Use the following guidelines to decide which part of the version to increment:

| Change type | Bump | Example |
|---|---|---|
| Breaking API/behaviour change | **MAJOR** | `0.x.y → 1.0.0` |
| New feature, backward-compatible | **MINOR** | `0.1.0 → 0.2.0` |
| Bug fix, patch, or minor tweak | **PATCH** | `0.1.0 → 0.1.1` |

> While the project is in the `0.x` range, minor version bumps may include breaking changes.

## Pull request guidelines

* Use concise commit messages.
* Title your pull request using the format `[intervals-mcp-server] <brief description>`.
* Describe any manual testing you performed and confirm whether `ruff`, `mypy`, and `pytest` passed.

We appreciate your contributions and your attention to these guidelines. Happy coding!
