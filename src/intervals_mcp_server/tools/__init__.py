"""
MCP tools registry for Intervals.icu MCP Server.

Importing this package registers every MCP tool with the shared FastMCP
instance: each tool module registers its tools via @mcp.tool() decorators
when it is imported.

Every tool is read-only. The server cannot create, modify or delete data on
Intervals.icu; the API client only ever issues GET requests.
"""

# Import all tools for re-export
# Note: Tools register themselves via @mcp.tool() decorators when imported
from intervals_mcp_server.tools.training_summary import get_training_summary  # noqa: F401
from intervals_mcp_server.tools.activities import (  # noqa: F401
    get_activities,
    get_activity_details,
    get_activity_histogram,
    get_activity_intervals,
    get_activity_messages,
    get_activity_streams,
)
from intervals_mcp_server.tools.activity_analysis import (  # noqa: F401
    get_activity_best_efforts,
    get_activity_curve,
    get_activity_hr_load_model,
    get_activity_interval_stats,
    get_activity_map,
    get_activity_power_spike_model,
    get_activity_power_vs_hr,
    get_activity_segments,
    get_activity_time_at_hr,
    get_activity_weather_summary,
)
from intervals_mcp_server.tools.activity_search import (  # noqa: F401
    get_activities_around,
    get_activities_by_ids,
    get_activity_tags,
    interval_search,
    search_activities,
)
from intervals_mcp_server.tools.events import (  # noqa: F401
    get_event_by_id,
    get_events,
    get_races,
)
from intervals_mcp_server.tools.athlete import get_athlete_zones  # noqa: F401
from intervals_mcp_server.tools.custom_items import (  # noqa: F401
    get_custom_item_by_id,
    get_custom_items,
)
from intervals_mcp_server.tools.power_curves import get_athlete_power_curves  # noqa: F401
from intervals_mcp_server.tools.training_plan import get_training_plan  # noqa: F401
from intervals_mcp_server.tools.wellness import get_wellness_data  # noqa: F401
from intervals_mcp_server.tools.workout_library import (  # noqa: F401
    get_workout,
    get_workout_folders,
    list_workouts,
)


__all__ = [
    # Activities
    "get_activities",
    "get_activity_details",
    "get_activity_histogram",
    "get_activity_intervals",
    "get_activity_messages",
    "get_activity_streams",
    # Activity search/discovery
    "search_activities",
    "interval_search",
    "get_activities_around",
    "get_activities_by_ids",
    "get_activity_tags",
    # Activity analysis
    "get_activity_curve",
    "get_activity_best_efforts",
    "get_activity_segments",
    "get_activity_time_at_hr",
    "get_activity_weather_summary",
    "get_activity_interval_stats",
    "get_activity_map",
    "get_activity_power_vs_hr",
    "get_activity_hr_load_model",
    "get_activity_power_spike_model",
    # Events
    "get_events",
    "get_races",
    "get_event_by_id",
    # Custom items
    "get_custom_items",
    "get_custom_item_by_id",
    # Other
    "get_wellness_data",
    "get_athlete_zones",
    "get_athlete_power_curves",
    "get_training_summary",
    # Training plans
    "get_training_plan",
    # Workout library
    "get_workout_folders",
    "list_workouts",
    "get_workout",
]
