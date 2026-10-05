"""
Shared pytest configuration.

Credentials come only from the environment, so the tests pin API_KEY and
ATHLETE_ID to fixed fake values before anything imports the server. This keeps
URL assertions such as "/athlete/i1/..." stable and guarantees the suite never
talks to Intervals.icu with a real key from the developer's shell or a .env file.
"""

import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

# Set before any intervals_mcp_server import; python-dotenv does not override
# variables that are already set, so a local .env cannot leak into the tests.
os.environ["API_KEY"] = "test"
os.environ["ATHLETE_ID"] = "i1"


@pytest.fixture(autouse=True)
def _pin_config(monkeypatch):
    """Reset the shared config singleton to the fake credentials for every test."""
    from intervals_mcp_server.config import get_config  # pylint: disable=import-outside-toplevel

    cfg = get_config()
    monkeypatch.setattr(cfg, "api_key", "test")
    monkeypatch.setattr(cfg, "athlete_id", "i1")
