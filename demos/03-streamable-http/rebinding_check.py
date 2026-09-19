"""Shows the HTTP server refusing requests that claim to come from another site.

A DNS rebinding attack tricks your browser into sending requests to a server on
127.0.0.1 while the page believes it's talking to some public site. The request still
carries that site's name in its Host and Origin headers, so a server that checks those
headers can turn it away. This script sends the same request twice, once with honest
headers and once with forged ones, and prints what the server says.

Start http_server.py in another terminal first, then run:

    uv run rebinding_check.py
"""

from __future__ import annotations

import http.client
import json

HOST, PORT, PATH = "127.0.0.1", 8765, "/mcp"

# A legacy initialize request is the simplest message every MCP server accepts as a
# first contact, which keeps this check independent of the protocol era.
BODY = json.dumps({
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2025-11-25", "capabilities": {},
               "clientInfo": {"name": "rebinding-check", "version": "1.0.0"}},
})


def send(label: str, host_header: str, origin: str) -> None:
    conn = http.client.HTTPConnection(HOST, PORT, timeout=10)
    conn.request("POST", PATH, body=BODY, headers={
        "Host": host_header,
        "Origin": origin,
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    })
    response = conn.getresponse()
    text = " ".join(response.read().decode(errors="replace").split())
    conn.close()
    verdict = "accepted" if response.status == 200 else "rejected"
    print(f"{label}\n  Host: {host_header}\n  Origin: {origin}\n"
          f"  -> {response.status} {response.reason} ({verdict}) {text[:80]}\n")


if __name__ == "__main__":
    send("Request from a page served by this machine", f"127.0.0.1:{PORT}",
         f"http://127.0.0.1:{PORT}")
    send("Request from a rebinding attack page", f"attacker.example:{PORT}",
         "http://attacker.example")
