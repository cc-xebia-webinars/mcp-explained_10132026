"""Exercises the service catalog server from a Python MCP client, without Copilot.

It's a quick way to prove the server works before an AI model gets involved. The
client launches server.py over stdio exactly the way VS Code does, then lists and
calls each kind of primitive.

    uv run check_server.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

HERE = Path(__file__).resolve().parent


def show(label: str, value: object) -> None:
    print(f"\n== {label}")
    print(value if isinstance(value, str) else json.dumps(value, indent=2))


async def main() -> None:
    server = StdioServerParameters(command=sys.executable, args=[str(HERE / "server.py")],
                                   cwd=str(HERE))
    async with Client(server) as client:
        tools = await client.list_tools()
        show("Tools", [t.name for t in tools.tools])

        resources = await client.list_resources()
        templates = await client.list_resource_templates()
        show("Resources", [str(r.uri) for r in resources.resources]
             + [t.uri_template for t in templates.resource_templates])

        prompts = await client.list_prompts()
        show("Prompts", [p.name for p in prompts.prompts])

        result = await client.call_tool("get_service", {"name": "payments-api"})
        show("Tool call: get_service(payments-api)", result.structured_content)

        result = await client.call_tool("get_service", {"name": "payments"})
        show("Tool call with a bad name (the model sees this error)",
             result.content[0].text if result.is_error else "unexpected success")

        runbook = await client.read_resource("catalog://services/payments-api/runbook")
        show("Resource: catalog://services/payments-api/runbook", runbook.contents[0].text)

        prompt = await client.get_prompt("incident_briefing", {"service": "checkout-web"})
        show("Prompt: incident_briefing(checkout-web)", prompt.messages[0].content.text)


if __name__ == "__main__":
    asyncio.run(main())
