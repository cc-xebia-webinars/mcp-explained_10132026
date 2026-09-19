"""Connects to the running HTTP server as a second client, alongside Copilot.

With stdio, every host starts its own private copy of the server. Over HTTP, any
number of clients share one running server, and therefore one database. This script
opens an incident through the server, and Copilot can see it straight away.

Start http_server.py in another terminal first, then run:

    uv run http_client.py
"""

from __future__ import annotations

import asyncio

from mcp import Client

URL = "http://127.0.0.1:8765/mcp"


async def main() -> None:
    async with Client(URL) as client:
        info = client.server_info
        print(f"Connected to {info.name} {info.version} over Streamable HTTP")
        print(f"Protocol version: {client.protocol_version}\n")

        result = await client.call_tool("create_incident", {
            "service": "catalog-search",
            "title": "Search results missing new autumn products",
            "severity": "sev3",
        })
        incident = result.structured_content
        print(f"Opened incident {incident['id']}: {incident['title']}\n")

        result = await client.call_tool("list_open_incidents", {})
        print("Open incidents, as every client of this server now sees them:")
        for i in result.structured_content["result"]:
            print(f"  #{i['id']} {i['severity']} {i['service']}: {i['title']}")


if __name__ == "__main__":
    asyncio.run(main())
