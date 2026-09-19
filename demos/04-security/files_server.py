"""A small file server for the security demo, limited to one root folder.

The root is set when the server starts. VS Code passes it from .vscode/mcp.json, so
changing what the server can see is a one-line configuration change:

    uv run files_server.py --root shared-docs
"""

from __future__ import annotations

import argparse
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from call_log import ToolCallLog

parser = argparse.ArgumentParser(description="Serve the files under one folder over MCP.")
parser.add_argument("--root", required=True, help="the only folder this server may read")
ROOT = Path(parser.parse_args().root).resolve()

# Every tool call is recorded in data/tool-calls.log. See call_log.py.
mcp = MCPServer("files", version="1.0.0", middleware=[ToolCallLog("files")])
READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)

# Folders that hold tooling rather than documents. Skipping them keeps the listing
# short when the root is the whole project.
SKIP = {".venv", ".vscode", "__pycache__", "data"}


def inside_root(relative_path: str) -> Path:
    """Resolve a path from the model and refuse anything outside the root.

    resolve() expands ".." and follows symbolic links before the check, so neither
    "../private/fake-credentials.txt" nor a link pointing out of the root gets past.
    """
    target = (ROOT / relative_path).resolve()
    if not target.is_relative_to(ROOT):
        raise ToolError(f"{relative_path!r} is outside the folder this server may read.")
    return target


@mcp.tool(annotations=READ_ONLY)
def list_files() -> list[str]:
    """List every file this server can read, as paths relative to its root folder."""
    files = []
    for path in sorted(ROOT.rglob("*")):
        parts = path.relative_to(ROOT).parts
        if path.is_file() and not SKIP.intersection(parts):
            files.append("/".join(parts))
    return files


@mcp.tool(annotations=READ_ONLY)
def read_file(path: str) -> str:
    """Read a text file. The path is relative to the server's root folder."""
    target = inside_root(path)
    if not target.is_file():
        raise ToolError(f"There's no file at {path!r}. Call list_files to see what exists.")
    return target.read_text(encoding="utf-8")[:20_000]


if __name__ == "__main__":
    mcp.run(transport="stdio")
