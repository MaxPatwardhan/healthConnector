"""
Custom items MCP tools for Intervals.icu.

This module contains read-only tools for retrieving athlete custom items (charts, fields, zones, etc.).
"""

from mcp.types import ToolAnnotations

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.formatting import format_custom_item_details
from intervals_mcp_server.utils.validation import resolve_athlete_id

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Custom Items", read_only_hint=True, destructive_hint=False
    )
)
async def get_custom_items() -> str:
    """Get custom items (charts, custom fields, zones, etc.) for an athlete from Intervals.icu"""
    athlete_id_to_use, error_msg = resolve_athlete_id(config.athlete_id)
    if error_msg:
        return error_msg

    result = await make_intervals_request(url=f"/athlete/{athlete_id_to_use}/custom-item")

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching custom items: {result.get('message')}"

    if not result:
        return f"No custom items found for athlete {athlete_id_to_use}."

    output = "Custom Items:\n\n"
    for item in result:
        if isinstance(item, dict):
            output += f"- ID: {item.get('id')}\n"
            output += f"  Name: {item.get('name', 'N/A')}\n"
            output += f"  Type: {item.get('type', 'N/A')}\n"
            if item.get("description"):
                output += f"  Description: {item['description']}\n"
            output += "\n"
    return output


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Custom Item by ID", read_only_hint=True, destructive_hint=False
    )
)
async def get_custom_item_by_id(
    item_id: int,
) -> str:
    """Get detailed information for a specific custom item from Intervals.icu

    Args:
        item_id: The custom item ID
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(config.athlete_id)
    if error_msg:
        return error_msg

    result = await make_intervals_request(url=f"/athlete/{athlete_id_to_use}/custom-item/{item_id}")

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching custom item: {result.get('message')}"

    if not result or not isinstance(result, dict):
        return f"No custom item found with ID {item_id}."

    return format_custom_item_details(result)
