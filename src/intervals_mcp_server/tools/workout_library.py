"""
Workout library MCP tools for Intervals.icu.

This module contains read-only tools for browsing the workout library,
including folders, listing workouts and getting a single workout.
"""

import json
from typing import Any

from mcp.types import ToolAnnotations

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.validation import resolve_athlete_id

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()

# Fields returned per folder by get_workout_folders
_FOLDER_FIELDS: list[str] = [
    "id",
    "name",
    "type",
    "num_workouts",
    "visibility",
    "description",
    "activity_types",
]

# Fields returned per workout in compact mode
_WORKOUT_COMPACT_FIELDS: list[str] = [
    "id",
    "name",
    "type",
    "folder_id",
    "moving_time",
    "icu_training_load",
    "tags",
]

# Additional fields returned per workout in full list mode (no workout_doc)
_WORKOUT_FULL_EXTRA_FIELDS: list[str] = [
    "description",
    "distance",
    "indoor",
    "color",
    "updated",
]


def _pick_fields(record: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """Return a new dict containing only the requested keys that exist and are non-empty."""
    result: dict[str, Any] = {}
    for key in fields:
        value = record.get(key)
        if value is None:
            continue
        # Keep 0 for folder_id (valid root sentinel) but omit other zero numerics
        if isinstance(value, (int, float)) and value == 0 and key != "folder_id":
            continue
        if isinstance(value, str) and not value:
            continue
        if isinstance(value, list) and not value:
            continue
        result[key] = value
    return result


def _strip_folder(folder: dict[str, Any], requesting_athlete_id: str = "") -> dict[str, Any]:
    """Strip children from a folder record and return only metadata fields.

    When *requesting_athlete_id* is provided the returned dict includes a
    ``shared`` boolean that is ``True`` when the folder's ``athlete_id``
    differs from the requesting athlete (i.e. the folder is not owned by the
    user).  When the comparison cannot be made the field defaults to ``False``.
    """
    result = _pick_fields(folder, _FOLDER_FIELDS)
    if requesting_athlete_id:
        folder_owner = folder.get("athlete_id")
        result["shared"] = (
            str(folder_owner) != requesting_athlete_id if folder_owner is not None else False
        )
    return result


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True, destructive_hint=False, title="Get Workout Folders"
    )
)
async def get_workout_folders() -> str:
    """Get workout library folders for an athlete from Intervals.icu.

    Returns folder/plan metadata (id, name, type, num_workouts, visibility,
    description, activity_types). The ``children`` field is always stripped —
    use ``list_workouts(folder_id=...)`` to browse workouts inside a folder.

    This is typically the first call an agent should make when exploring the
    workout library.

    Related tools:
        - ``list_workouts`` — list workouts, optionally filtered by folder
        - ``get_workout`` — fetch full workout detail including steps
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(config.athlete_id)
    if error_msg:
        return error_msg

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/folders",
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching workout folders: {result.get('message')}"

    if not result:
        return f"No workout folders found for athlete {athlete_id_to_use}."

    folders: list[dict[str, Any]]
    if isinstance(result, list):
        folders = [
            _strip_folder(f, requesting_athlete_id=athlete_id_to_use)
            for f in result
            if isinstance(f, dict)
        ]
    elif isinstance(result, dict):
        folders = [_strip_folder(result, requesting_athlete_id=athlete_id_to_use)]
    else:
        return "Unexpected response format from folders endpoint."

    if not folders:
        return f"No workout folders found for athlete {athlete_id_to_use}."

    return json.dumps(folders, separators=(",", ":"))


def _find_folder_children(
    folders: list[dict[str, Any]], target_id: int
) -> list[dict[str, Any]] | None:
    """Recursively search *folders* for one whose ``id`` equals *target_id*.

    Returns the folder's ``children`` list (which contains workout records) or
    ``None`` when the folder is not found.  Folders may be nested, so this
    performs a depth-first search through each folder's ``children`` that are
    themselves folders (dicts with an ``id`` key and their own ``children``).
    """
    for folder in folders:
        if not isinstance(folder, dict):
            continue
        if folder.get("id") == target_id:
            children = folder.get("children")
            if isinstance(children, list):
                return [c for c in children if isinstance(c, dict)]
            return []
        # Recurse into nested folders
        nested = folder.get("children")
        if isinstance(nested, list):
            sub_folders = [c for c in nested if isinstance(c, dict) and "children" in c]
            if sub_folders:
                found = _find_folder_children(sub_folders, target_id)
                if found is not None:
                    return found
    return None


@mcp.tool(
    annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, title="List Workouts")
)
async def list_workouts(
    folder_id: int | None = None,
    compact: bool = True,
    workout_type: str = "",
) -> str:
    """List workouts in the athlete's workout library on Intervals.icu.

    Use ``get_workout_folders`` first to discover folder IDs, then pass a
    ``folder_id`` to filter results to a specific folder.

    Supports both the athlete's own workouts and shared workouts.  When a
    ``folder_id`` is provided, the tool also queries the folders endpoint so
    that workouts inside shared folders/plans are included.

    ``workout_doc`` (step-by-step structure) is never included in list output.
    Use ``get_workout(workout_id)`` to expand a specific workout.

    Args:
        folder_id: Filter to workouts in this folder only (optional).
                   Works for both own and shared folders.
        compact: If True (default), return a brief summary per workout to save tokens.
                 Full mode adds description, distance, indoor, color, and updated fields.
        workout_type: Filter by activity type, e.g. "Ride", "Run", "Swim" (optional, case-insensitive).
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(config.athlete_id)
    if error_msg:
        return error_msg

    # Always fetch the athlete's own workouts from /workouts
    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/workouts",
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching workouts: {result.get('message')}"

    own_workouts: list[dict[str, Any]] = []
    if isinstance(result, list):
        own_workouts = [w for w in result if isinstance(w, dict)]

    workouts: list[dict[str, Any]] = []
    shared: bool = False

    if folder_id is not None:
        # Filter own workouts by folder
        workouts = [w for w in own_workouts if w.get("folder_id") == folder_id]

        # If no own workouts matched, the folder may be shared.
        # Fetch the folders endpoint and look for the target folder's children.
        if not workouts:
            folders_result = await make_intervals_request(
                url=f"/athlete/{athlete_id_to_use}/folders",
            )
            if isinstance(folders_result, list):
                children = _find_folder_children(folders_result, folder_id)
                if children is not None:
                    workouts = children
                    shared = True
    else:
        workouts = own_workouts

    # Apply workout_type filter (case-insensitive)
    if workout_type:
        type_lower = workout_type.lower()
        workouts = [w for w in workouts if str(w.get("type", "")).lower() == type_lower]

    if not workouts:
        msg = f"No workouts found for athlete {athlete_id_to_use}"
        if folder_id is not None:
            msg += f" in folder {folder_id}"
        if workout_type:
            msg += f" with type '{workout_type}'"
        return msg + "."

    fields = list(_WORKOUT_COMPACT_FIELDS)
    if not compact:
        fields += _WORKOUT_FULL_EXTRA_FIELDS

    output = [_pick_fields(w, fields) for w in workouts]

    if shared:
        return json.dumps(
            {"shared": True, "workouts": output},
            separators=(",", ":"),
        )
    return json.dumps(output, separators=(",", ":"))


@mcp.tool(
    annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, title="Get Workout")
)
async def get_workout(
    workout_id: int,
) -> str:
    """Get full detail for a single workout from the Intervals.icu library, including workout_doc steps.

    Use ``list_workouts`` to discover workout IDs first.

    Related tools:
        - ``get_workout_folders`` — browse folder structure
        - ``list_workouts`` — list workouts without step detail

    Args:
        workout_id: The workout ID to retrieve
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(config.athlete_id)
    if error_msg:
        return error_msg

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/workouts/{workout_id}",
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching workout: {result.get('message')}"

    if not result or not isinstance(result, dict):
        return f"No workout found with ID {workout_id}."

    return json.dumps(result, separators=(",", ":"))
