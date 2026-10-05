"""
Training plan MCP tools for Intervals.icu.

Read-only tool for getting the athlete's active training plan.
"""

import json

from mcp.types import ToolAnnotations

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.validation import resolve_athlete_id
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Training Plan", read_only_hint=True, destructive_hint=False
    )
)
async def get_training_plan() -> str:
    """Get the athlete's current training plan, if any."""
    athlete_id_to_use, error_msg = resolve_athlete_id(config.athlete_id)
    if error_msg:
        return error_msg

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/training-plan",
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching training plan: {result.get('message', 'Unknown error')}"

    if not result:
        return f"No active training plan for athlete {athlete_id_to_use}."

    return json.dumps(result, indent=2, default=str)
