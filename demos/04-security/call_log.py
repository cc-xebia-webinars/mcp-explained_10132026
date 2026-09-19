"""Records every tool call a server receives, as one line of JSON per call.

When something goes wrong, the log answers the questions that matter: which tool
ran, with which arguments, when, and whether it failed. It's attached to the servers
you own, through the SDK's middleware hook. You can't rely on a third-party server to
log honestly, so for those, logging belongs in the host or a proxy in front of them.

The log is written to data/tool-calls.log, which git ignores.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LOG_PATH = Path(__file__).resolve().parent / "data" / "tool-calls.log"


class ToolCallLog:
    """SDK middleware that appends a record of each tools/call request to the log."""

    def __init__(self, server: str) -> None:
        self.server = server

    async def __call__(self, ctx: Any, call_next: Any) -> Any:
        # Middleware sees every message, including list requests. Only calls matter here.
        if ctx.method != "tools/call":
            return await call_next(ctx)
        params = ctx.params if isinstance(ctx.params, dict) else {}
        entry = {
            "time": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "server": self.server,
            "tool": params.get("name"),
            "arguments": params.get("arguments", {}),
        }
        try:
            result = await call_next(ctx)
            failed = getattr(result, "is_error", None)
            if failed is None and isinstance(result, dict):
                failed = result.get("isError")
            entry["outcome"] = "error" if failed else "ok"
            return result
        except Exception as exc:
            entry["outcome"] = f"protocol error: {exc}"
            raise
        finally:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with LOG_PATH.open("a", encoding="utf-8") as log:
                log.write(json.dumps(entry) + "\n")
