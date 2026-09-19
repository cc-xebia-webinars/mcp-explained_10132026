"""Serves the service catalog over Streamable HTTP, but only to callers with a token.

The plain HTTP server in http_server.py answers anyone who can reach it. This one
turns away any request that doesn't carry the right bearer token, before the request
gets anywhere near MCP. The token is printed when the server starts, standing in for
the access token an OAuth sign-in would give you.

    uv run secure_http_server.py

In production you'd use OAuth instead of a shared token. The SDK supports that through
MCPServer's token_verifier and auth arguments, which validate tokens issued by your
identity provider and publish the metadata clients like VS Code use to sign people in.
"""

from __future__ import annotations

import os
import secrets

import uvicorn

from server import mcp

HOST = "127.0.0.1"
PORT = 8766  # a different port, so this can run next to http_server.py

# Set CATALOG_TOKEN to reuse a token across restarts. Otherwise every start gets a
# fresh random one, so a token from a previous run stops working.
TOKEN = os.environ.get("CATALOG_TOKEN") or secrets.token_urlsafe(24)


class RequireBearerToken:
    """ASGI middleware that rejects any HTTP request without the expected bearer token."""

    def __init__(self, app, token: str) -> None:
        self.app = app
        self.expected = f"Bearer {token}".encode()

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            # Startup and shutdown events aren't requests, so they pass straight through.
            await self.app(scope, receive, send)
            return
        supplied = dict(scope["headers"]).get(b"authorization", b"")
        # compare_digest takes the same time wherever the first difference is, so the
        # response time can't be used to guess the token one character at a time.
        if secrets.compare_digest(supplied, self.expected):
            await self.app(scope, receive, send)
            return
        body = b'{"error": "invalid_token"}'
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"www-authenticate", b'Bearer realm="service-catalog"'),
            ],
        })
        await send({"type": "http.response.body", "body": body})


if __name__ == "__main__":
    # streamable_http_app builds the same app that mcp.run uses, including DNS
    # rebinding protection for a loopback host. The middleware wraps it from outside.
    app = RequireBearerToken(mcp.streamable_http_app(host=HOST), TOKEN)
    print(f"Service catalog listening on http://{HOST}:{PORT}/mcp (press Ctrl+C to stop)")
    print(f"Bearer token: {TOKEN}", flush=True)
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
