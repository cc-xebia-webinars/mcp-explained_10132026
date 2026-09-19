"""Serves the same service catalog over Streamable HTTP instead of stdio.

The tools, resources, and prompts don't change at all. They're defined in server.py,
which is identical to the file in Demo 2. Only the way the server is reached changes:
it becomes a long-running web service at a URL, rather than a child process that VS
Code starts and talks to over stdin and stdout.

    uv run http_server.py
"""

from server import mcp

# 127.0.0.1 means only programs on this machine can connect. Listening on 0.0.0.0
# would put an unauthenticated server, with a tool that writes to the database, on
# every network this laptop joins.
HOST = "127.0.0.1"
PORT = 8765

if __name__ == "__main__":
    print(f"Service catalog listening on http://{HOST}:{PORT}/mcp (press Ctrl+C to stop)")
    # Because HOST is a loopback address, the SDK also switches on DNS rebinding
    # protection, which rejects requests whose Host or Origin header names some other
    # site. That stops a malicious web page in your browser from reaching this server.
    mcp.run(transport="streamable-http", host=HOST, port=PORT)
