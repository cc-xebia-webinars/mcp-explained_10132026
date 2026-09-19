"""Lists every tool the local servers in .vscode/mcp.json offer, and flags risky ones.

The model reads each tool's full description, but the person approving a server
usually never sees it. This script reads the same configuration VS Code reads, starts
each stdio server, and prints what the model would be told, so you can review it the
way you'd review a dependency before adding it.

Once you're happy with what you see, pin it. --approve records a fingerprint of every
tool in approved-tools.json, and every later run compares against those fingerprints,
so a server that changes its tools after you approved them gets caught.

    uv run audit_tools.py --approve
    uv run audit_tools.py
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import textwrap
from pathlib import Path

from mcp import Client, StdioServerParameters

HERE = Path(__file__).resolve().parent
CONFIG = HERE / ".vscode" / "mcp.json"
APPROVED = HERE / "approved-tools.json"

# Phrases that have no business in an honest tool description. None of them proves
# bad intent on its own, but each one is worth a human look.
WARNING_SIGNS = {
    r"<important>|<system>|<instructions?>": "markup that tries to look like system instructions",
    r"\b(do not|don't|never) (tell|mention|inform|reveal)": "asks the model to hide something from the user",
    r"ignore (all |any )?(previous|prior|other)": "asks the model to ignore other instructions",
    r"credential|password|secret|api[ _-]?key|token|\.env\b": "mentions secrets or credential files",
    r"before (using|calling) this tool, call": "tells the model to call a different tool first",
}


def expand(value: str) -> str:
    return value.replace("${workspaceFolder}", str(HERE))


def fingerprint(tool) -> str:
    """Hash everything the model sees about a tool, so any change shows up."""
    seen = {"description": tool.description, "input_schema": tool.input_schema,
            "annotations": tool.annotations.model_dump() if tool.annotations else None}
    return hashlib.sha256(json.dumps(seen, sort_keys=True).encode()).hexdigest()[:16]


def warnings_for(tool) -> list[str]:
    found = [reason for pattern, reason in WARNING_SIGNS.items()
             if re.search(pattern, tool.description or "", re.IGNORECASE)]
    hints = tool.annotations
    if not (hints and hints.read_only_hint):
        found.append("not marked read-only, so it may change data")
    return found


async def audit(name: str, entry: dict, approved: dict[str, str] | None) -> dict[str, str]:
    print(f"\n### Server: {name}")
    print(f"    command: {entry['command']} {' '.join(entry.get('args', []))}")
    params = StdioServerParameters(
        command=shutil.which(entry["command"]) or entry["command"],
        args=[expand(a) for a in entry.get("args", [])],
        # Pass the same environment VS Code would, including anything set in mcp.json.
        env={**os.environ, **entry.get("env", {})},
        cwd=expand(entry.get("cwd", "${workspaceFolder}")),
    )
    prints: dict[str, str] = {}
    async with Client(params) as client:
        for tool in (await client.list_tools()).tools:
            key = f"{name}/{tool.name}"
            prints[key] = fingerprint(tool)
            print(f"\n  Tool: {tool.name}   fingerprint {prints[key]}")
            print(textwrap.indent((tool.description or "(no description)").strip(), "    | ",
                                  predicate=lambda line: True))
            print(f"    arguments: {', '.join(tool.input_schema.get('properties', {})) or '(none)'}")
            for warning in warnings_for(tool):
                print(f"    WARNING: {warning}")
            if approved is not None:
                if key not in approved:
                    print("    CHANGED: this tool is new since you approved the server")
                elif approved[key] != prints[key]:
                    print("    CHANGED: this tool's description or arguments differ from what you approved")
    return prints


async def main() -> None:
    parser = argparse.ArgumentParser(description="Review and pin the tools of local MCP servers.")
    parser.add_argument("--approve", action="store_true",
                        help="record the current tools as approved")
    args = parser.parse_args()

    approved = None
    if not args.approve and APPROVED.exists():
        approved = json.loads(APPROVED.read_text(encoding="utf-8"))

    servers = json.loads(CONFIG.read_text(encoding="utf-8"))["servers"]
    current: dict[str, str] = {}
    for name, entry in servers.items():
        if entry.get("type", "stdio") == "stdio":
            current |= await audit(name, entry, approved)

    if args.approve:
        APPROVED.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        print(f"\nApproved {len(current)} tools. Fingerprints saved to {APPROVED.name}.")
    elif approved is not None:
        for key in sorted(set(approved) - set(current)):
            print(f"\nCHANGED: {key} was approved but no longer exists")
    else:
        print("\nNo approved fingerprints yet. Run with --approve once you're happy with these tools.")


if __name__ == "__main__":
    asyncio.run(main())
