"""
Event-related MCP tools for Intervals.icu.

This module contains read-only tools for retrieving athlete events.
"""

from mcp.types import ToolAnnotations

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.dates import get_date_days_ahead, get_todays_date
from intervals_mcp_server.utils.formatting import (
    format_event_compact,
    format_event_details,
    format_event_summary,
)
from intervals_mcp_server.utils.validation import (
    resolve_athlete_id,
)

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()

# Known event categories from the Intervals.icu API
VALID_EVENT_CATEGORIES: set[str] = {
    "WORKOUT",
    "RACE_A",
    "RACE_B",
    "RACE_C",
    "NOTE",
    "PLAN",
    "HOLIDAY",
    "SICK",
    "INJURED",
    "SET_EFTP",
    "FITNESS_DAYS",
    "SEASON_START",
    "TARGET",
    "SET_FITNESS",
}


RACE_CATEGORIES = "RACE_A,RACE_B,RACE_C"


@mcp.tool(
    annotations=ToolAnnotations(title="Get Races", read_only_hint=True, destructive_hint=False)
)
async def get_races(
    start_date: str = "",
    end_date: str = "",
    compact: bool = True,
) -> str:
    """Get races for an athlete from Intervals.icu.

    Retrieves all race events (A, B, and C priority) over a date range.
    Defaults to a one-year window (today to 365 days ahead) which is larger
    than other tools because races are typically planned well in advance.

    Args:
        start_date: Start date in YYYY-MM-DD format (optional, defaults to today)
        end_date: End date in YYYY-MM-DD format (optional, defaults to 365 days from today)
        compact: If True, return a brief one-line-per-event summary to save tokens (optional, defaults to True)
    """
    # Resolve athlete ID
    athlete_id_to_use, error_msg = resolve_athlete_id(config.athlete_id)
    if error_msg:
        return error_msg

    # Parse date parameters (races use a larger default window of 1 year)
    if not start_date:
        start_date = get_todays_date()
    if not end_date:
        end_date = get_date_days_ahead(days_ahead=365)

    # Call the Intervals.icu API with race category filter
    params: dict[str, str] = {
        "oldest": start_date,
        "newest": end_date,
        "category": RACE_CATEGORIES,
    }

    result = await make_intervals_request(url=f"/athlete/{athlete_id_to_use}/events", params=params)

    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error fetching races: {error_message}"

    # Format the response
    if not result:
        return f"No races found for athlete {athlete_id_to_use} in the specified date range."

    # Ensure result is a list
    events = result if isinstance(result, list) else []

    if not events:
        return f"No races found for athlete {athlete_id_to_use} in the specified date range."

    formatter = format_event_compact if compact else format_event_summary
    races_summary = "Races:\n\n"
    for event in events:
        if not isinstance(event, dict):
            continue

        races_summary += formatter(event) + "\n"

    return races_summary


@mcp.tool(
    annotations=ToolAnnotations(title="Get Events", read_only_hint=True, destructive_hint=False)
)
async def get_events(
    start_date: str = "",
    end_date: str = "",
    compact: bool = True,
    category: str = "",
) -> str:
    """Get events for an athlete from Intervals.icu

    Args:
        start_date: Start date in YYYY-MM-DD format (optional, defaults to today)
        end_date: End date in YYYY-MM-DD format (optional, defaults to 30 days from today)
        compact: If True, return a brief one-line-per-event summary to save tokens (optional, defaults to True)
        category: Filter events by category. Comma-separated list of categories to include
            (e.g. "NOTE", "HOLIDAY,RACE_A", "WORKOUT,NOTE"). Valid categories: WORKOUT,
            RACE_A, RACE_B, RACE_C, NOTE, PLAN, HOLIDAY, SICK, INJURED, SET_EFTP,
            FITNESS_DAYS, SEASON_START, TARGET, SET_FITNESS. Returns an error if an invalid
            category is provided. If not provided, all events are returned.
    """
    # Resolve athlete ID
    athlete_id_to_use, error_msg = resolve_athlete_id(config.athlete_id)
    if error_msg:
        return error_msg

    # Parse date parameters (events use different defaults)
    if not start_date:
        start_date = get_todays_date()
    if not end_date:
        end_date = get_date_days_ahead()

    # Parse category filter
    category_filter: str | None = None
    if category:
        parsed = {c.strip().upper() for c in category.split(",")}
        invalid = parsed - VALID_EVENT_CATEGORIES
        if invalid:
            return (
                f"Error: Invalid event category: {', '.join(sorted(invalid))}. "
                f"Valid categories are: {', '.join(sorted(VALID_EVENT_CATEGORIES))}."
            )
        category_filter = ",".join(sorted(parsed))

    # Call the Intervals.icu API
    params: dict[str, str] = {"oldest": start_date, "newest": end_date}
    if category_filter:
        params["category"] = category_filter

    result = await make_intervals_request(url=f"/athlete/{athlete_id_to_use}/events", params=params)

    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error fetching events: {error_message}"

    # Format the response
    if not result:
        return f"No events found for athlete {athlete_id_to_use} in the specified date range."

    # Ensure result is a list
    events = result if isinstance(result, list) else []

    if not events:
        return f"No events found for athlete {athlete_id_to_use} in the specified date range."

    formatter = format_event_compact if compact else format_event_summary
    events_summary = "Events:\n\n"
    for event in events:
        if not isinstance(event, dict):
            continue

        events_summary += formatter(event) + "\n"

    return events_summary


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Event by ID", read_only_hint=True, destructive_hint=False
    )
)
async def get_event_by_id(
    event_id: str,
) -> str:
    """Get detailed information for a specific event from Intervals.icu

    Args:
        event_id: The Intervals.icu event ID
    """
    # Resolve athlete ID
    athlete_id_to_use, error_msg = resolve_athlete_id(config.athlete_id)
    if error_msg:
        return error_msg

    # Call the Intervals.icu API
    result = await make_intervals_request(url=f"/athlete/{athlete_id_to_use}/events/{event_id}")

    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error fetching event details: {error_message}"

    # Format the response
    if not result:
        return f"No details found for event {event_id}."

    if not isinstance(result, dict):
        return f"Invalid event format for event {event_id}."

    return format_event_details(result)
