"""
Intervals.icu MCP Server (read-only)

This module implements a Model Context Protocol (MCP) server for connecting
Claude with the Intervals.icu API. It exposes read-only tools for athlete data:
activities and their analysis, wellness metrics, events and races, training
summaries, zones, power curves, training plans, workouts and custom items.

The server cannot create, modify or delete anything on Intervals.icu. The API
client only issues GET requests, and credentials (API_KEY, ATHLETE_ID) come only
from the environment, never from tool arguments.

Usage:
    The server loads configuration from environment variables (optionally via a
    .env file) and communicates with the Intervals.icu API.

    To run the server locally over stdio:
        $ python src/intervals_mcp_server/server.py

    To serve it over Streamable HTTP (for remote MCP clients):
        $ MCP_TRANSPORT=http python src/intervals_mcp_server/server.py

    See the README for the full tool list and deployment details.
"""

import logging

# Import API client and configuration
from intervals_mcp_server.api.client import (
    httpx_client,  # Re-export for backward compatibility with tests
    make_intervals_request,
)
from intervals_mcp_server.config import get_config
from intervals_mcp_server.mcp_instance import mcp

# Import types and validation
from intervals_mcp_server.server_setup import setup_transport, start_server
from intervals_mcp_server.utils.validation import validate_athlete_id

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("intervals_icu_mcp_server")

# Get configuration instance
config = get_config()

# Import tool modules to register them (tools register themselves via @mcp.tool() decorators)
# Import tool functions for re-export
from intervals_mcp_server.tools import (  # pylint: disable=wrong-import-position  # noqa: E402
    get_activities,
    get_activities_around,
    get_activities_by_ids,
    get_activity_best_efforts,
    get_activity_curve,
    get_activity_details,
    get_activity_histogram,
    get_activity_hr_load_model,
    get_activity_interval_stats,
    get_activity_intervals,
    get_activity_map,
    get_activity_messages,
    get_activity_power_spike_model,
    get_activity_power_vs_hr,
    get_activity_segments,
    get_activity_streams,
    get_activity_tags,
    get_activity_time_at_hr,
    get_activity_weather_summary,
    get_athlete_power_curves,
    get_athlete_zones,
    get_custom_item_by_id,
    get_custom_items,
    get_event_by_id,
    get_events,
    get_races,
    get_training_plan,
    get_training_summary,
    get_wellness_data,
    get_workout,
    get_workout_folders,
    interval_search,
    list_workouts,
    search_activities,
)

# Import resource modules to register them (resources register themselves via @mcp.resource() decorators)
from intervals_mcp_server.resources.guide import coaching_context_protocol  # pylint: disable=wrong-import-position  # noqa: E402

# Re-export make_intervals_request and httpx_client for backward compatibility
__all__ = [
    "make_intervals_request",
    "httpx_client",  # Re-exported for test compatibility
    "get_activities",
    "get_activities_around",
    "get_activities_by_ids",
    "get_activity_best_efforts",
    "get_activity_curve",
    "get_activity_details",
    "get_activity_histogram",
    "get_activity_hr_load_model",
    "get_activity_interval_stats",
    "get_activity_intervals",
    "get_activity_map",
    "get_activity_messages",
    "get_activity_power_spike_model",
    "get_activity_power_vs_hr",
    "get_activity_segments",
    "get_activity_streams",
    "get_activity_tags",
    "get_activity_time_at_hr",
    "get_activity_weather_summary",
    "get_athlete_power_curves",
    "get_athlete_zones",
    "get_custom_item_by_id",
    "get_custom_items",
    "get_event_by_id",
    "get_events",
    "get_races",
    "get_training_plan",
    "get_training_summary",
    "get_wellness_data",
    "get_workout",
    "get_workout_folders",
    "interval_search",
    "list_workouts",
    "search_activities",
    "coaching_context_protocol",
]


# Run the server
if __name__ == "__main__":
    # Validate ATHLETE_ID when server starts (not at import time to allow tests)
    validate_athlete_id(config.athlete_id)

    # Setup transport and start server
    selected_transport = setup_transport()
    start_server(mcp, selected_transport)
