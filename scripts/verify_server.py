"""Check a running server: list its tools over Streamable HTTP, fail if any
tool could mutate data or accepts credentials, and optionally call
get_wellness_data for the last N days.

Usage:
    uv run python scripts/verify_server.py URL [--token-env VAR] [--days N]

    # local, no auth
    uv run python scripts/verify_server.py http://127.0.0.1:8000/mcp --days 14
    # Prefect Horizon, with a Horizon API key (fmcp_...) in $HORIZON_TOKEN
    uv run python scripts/verify_server.py https://<name>.fastmcp.app/mcp --token-env HORIZON_TOKEN --days 14

The bearer token is read from the environment variable named by --token-env, so
it never appears on the command line or in the output.
"""

import argparse
import asyncio
import datetime as dt
import os
import sys

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

MUTATING_PREFIXES = (
    "add_",
    "apply_",
    "bulk_",
    "change_",
    "create_",
    "delete_",
    "remove_",
    "schedule_",
    "set_",
    "split_",
    "update_",
    "upload_",
    "edit_",
    "put_",
    "post_",
)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--token-env", default="")
    ap.add_argument("--days", type=int, default=0)
    args = ap.parse_args()

    headers = {}
    if args.token_env:
        token = os.environ.get(args.token_env, "")
        if not token:
            print(f"env var {args.token_env} is empty", file=sys.stderr)
            return 2
        headers["Authorization"] = f"Bearer {token}"

    transport = StreamableHttpTransport(args.url, headers=headers)
    async with Client(transport, timeout=60) as client:
        tools = await client.list_tools()
        bad = []
        print(f"{len(tools)} tools:")
        for t in sorted(tools, key=lambda t: t.name):
            ann = t.annotations
            ro = getattr(ann, "read_only_hint", None) if ann else None
            destr = getattr(ann, "destructive_hint", None) if ann else None
            params = sorted((t.input_schema or {}).get("properties", {}))
            print(f"  {t.name:32} readOnly={ro} destructive={destr} params={params}")
            if ro is not True or destr or t.name.startswith(MUTATING_PREFIXES):
                bad.append(t.name)
            if {"api_key", "athlete_id"} & set(params):
                bad.append(f"{t.name}(credential param)")
        print("MUTATING/SUSPECT:", bad or "none")

        if args.days:
            today = dt.date.today()
            start = today - dt.timedelta(days=args.days - 1)
            res = await client.call_tool(
                "get_wellness_data",
                {"start_date": start.isoformat(), "end_date": today.isoformat()},
            )
            for block in res.content:
                print(getattr(block, "text", block))
        return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
