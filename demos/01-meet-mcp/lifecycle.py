"""Walks through the MCP request/response lifecycle by sending raw JSON-RPC over stdio.

Hosts like VS Code use an MCP SDK and never show you these messages. This script
writes each one by hand and prints it, so you can see exactly what crosses the wire.

It works with servers from both eras of the protocol:

- Modern servers (protocol 2026-07-28 and later) are stateless. Every request carries
  the protocol version in its _meta field, and there's no handshake.
- Legacy servers (2025-11-25 and earlier) expect an initialize handshake first.

The script probes with server/discover, which only modern servers understand, and
falls back to the handshake if the server doesn't recognize it. That's the same
approach the specification recommends for real clients.

    uv run lifecycle.py filesystem --step
    uv run lifecycle.py hello --step

--step pauses before each phase, so you can talk through one phase at a time.
Leave it off to print the whole conversation at once.
"""

from __future__ import annotations

import argparse
import json
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTES = HERE / "notes"

MODERN_VERSION = "2026-07-28"
LEGACY_VERSION = "2025-11-25"
CLIENT_INFO = {"name": "lifecycle-demo", "version": "1.0.0"}

# The official filesystem server is written in TypeScript and published to npm. On
# Windows, npx is a .cmd script, so it has to be located rather than run by name.
NPX = shutil.which("npx") or "npx"

SERVERS = {
    "filesystem": {
        "command": [NPX, "-y", "@modelcontextprotocol/server-filesystem@2026.8.31", str(NOTES)],
        "tool": ("list_directory", {"path": str(NOTES)}),
    },
    "hello": {
        "command": [sys.executable, str(HERE / "hello_server.py")],
        "tool": ("say_hello", {"name": "webinar"}),
    },
}


class StdioConnection:
    """One server process, spoken to with newline-delimited JSON-RPC messages."""

    def __init__(self, command: list[str]) -> None:
        # The server's stderr is discarded to keep the output readable. Servers write
        # logs there precisely because stdout is reserved for protocol messages.
        self.proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        self.lines: queue.Queue[str] = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()
        self.next_id = 1

    def _read(self) -> None:
        for line in self.proc.stdout:
            self.lines.put(line)

    def request(self, method: str, params: dict) -> dict:
        message = {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params}
        self.next_id += 1
        self._send(message)
        while True:
            # A real client would wait asynchronously. A timeout is enough here, and
            # the spec allows treating a silent server as a legacy one.
            reply = json.loads(self.lines.get(timeout=60))
            show("server -> client", reply)
            if reply.get("id") == message["id"]:
                return reply

    def notify(self, method: str) -> None:
        # Notifications have no id, and the server never replies to them.
        self._send({"jsonrpc": "2.0", "method": method})

    def _send(self, message: dict) -> None:
        show("client -> server", message)
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def close(self) -> None:
        # On stdio, closing the server's input is how a client says it's finished.
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def show(direction: str, message: dict) -> None:
    print(f"  {direction}")
    text = json.dumps(abbreviate(message), indent=2)
    print("\n".join("    " + line for line in text.splitlines()))


def abbreviate(message: dict) -> dict:
    """Trim long tool lists and schemas so each message fits on a screen."""
    tools = message.get("result", {}).get("tools")
    if not tools:
        return message
    def clip(text: str) -> str:
        return text if len(text) <= 60 else text[:60] + "..."

    short = [{"name": t["name"], "description": clip(t.get("description", ""))}
             for t in tools[:4]]
    if len(tools) > 4:
        short.append(f"... and {len(tools) - 4} more tools")
    return {**message, "result": {**message["result"], "tools": short}}


PAUSE = False


def step(title: str) -> None:
    if PAUSE and not title.startswith("1."):
        input("\n  [press Enter for the next phase] ")
    print(f"\n=== {title}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Show the MCP lifecycle with raw JSON-RPC.")
    parser.add_argument("server", choices=SERVERS, help="which server to start")
    parser.add_argument("--step", action="store_true", help="pause before each phase")
    args = parser.parse_args()
    server = SERVERS[args.server]
    global PAUSE
    PAUSE = args.step

    conn = StdioConnection(server["command"])
    try:
        step("1. Probe: does this server speak the modern, stateless protocol?")
        meta = {
            "io.modelcontextprotocol/protocolVersion": MODERN_VERSION,
            "io.modelcontextprotocol/clientCapabilities": {},
            "io.modelcontextprotocol/clientInfo": CLIENT_INFO,
        }
        reply = conn.request("server/discover", {"_meta": meta})
        modern = "result" in reply

        if modern:
            print("\n  The server answered, so every request from here on carries _meta,")
            print("  and there's no handshake or session to set up.")
            params: dict = {"_meta": meta}
        else:
            print("\n  The server didn't recognize server/discover, so it's a legacy server.")
            step("2. Legacy handshake: agree on a version and exchange capabilities")
            conn.request("initialize", {
                "protocolVersion": LEGACY_VERSION,
                "capabilities": {},
                "clientInfo": CLIENT_INFO,
            })
            conn.notify("notifications/initialized")
            params = {}

        step("3. Discovery: ask which tools the server offers")
        conn.request("tools/list", params)

        name, arguments = server["tool"]
        step(f"4. Invocation: call the {name} tool")
        conn.request("tools/call", {**params, "name": name, "arguments": arguments})

        step("5. Shutdown: close the server's input stream")
        print("  On stdio there's no shutdown message. The client closes stdin and the")
        print("  server exits.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
