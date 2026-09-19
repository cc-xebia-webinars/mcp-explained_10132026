"""Sends the same request to the secure server three times: no token, wrong, and right.

Start secure_http_server.py in another terminal first, then pass the token it printed:

    uv run auth_check.py <token>
"""

from __future__ import annotations

import argparse
import http.client
import json

HOST, PORT, PATH = "127.0.0.1", 8766, "/mcp"

BODY = json.dumps({
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2025-11-25", "capabilities": {},
               "clientInfo": {"name": "auth-check", "version": "1.0.0"}},
})


def send(label: str, token: str | None) -> None:
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    conn = http.client.HTTPConnection(HOST, PORT, timeout=10)
    conn.request("POST", PATH, body=BODY, headers=headers)
    response = conn.getresponse()
    text = " ".join(response.read().decode(errors="replace").split())
    conn.close()
    verdict = "accepted" if response.status == 200 else "rejected"
    print(f"{label}\n  -> {response.status} {response.reason} ({verdict}) {text[:70]}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check the secure server's token handling.")
    parser.add_argument("token", help="the bearer token secure_http_server.py printed")
    args = parser.parse_args()
    send("Request with no token", None)
    send("Request with a wrong token", "not-the-right-token")
    send("Request with the printed token", args.token)
