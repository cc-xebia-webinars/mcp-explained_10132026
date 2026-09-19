"""An MCP server that exposes the team's service catalog to an AI agent.

It uses all three MCP primitives so you can compare them side by side:

- Tools are actions the model decides to call, like searching or opening an incident.
- Resources are read-only context the user or host chooses to attach, like a runbook.
- Prompts are reusable, parameterized instructions the user picks from a menu.

Run it over stdio, which is how VS Code starts it from .vscode/mcp.json:

    uv run server.py
"""

from __future__ import annotations

import sys
from typing import Literal, TypedDict

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp.types import ToolAnnotations

import catalog_db

mcp = MCPServer(
    "service-catalog",
    version="1.0.0",
    instructions=(
        "Answers questions about the company's internal services: who owns them, "
        "what they depend on, and which incidents are open."
    ),
)

# Read-only tools say so in their annotations. Hosts can use that hint to decide how
# much confirmation a call needs, although they shouldn't trust it from a server
# they don't trust.
READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)


# Typed return values become an output schema, so the host knows the shape of each
# result before it calls the tool, and the result arrives as structured JSON.

class ServiceSummary(TypedDict):
    name: str
    team: str
    tier: int
    description: str


class Service(ServiceSummary):
    channel: str
    on_call: str
    depends_on: list[str]
    used_by: list[str]


class Incident(TypedDict):
    id: int
    service: str
    title: str
    severity: str
    status: str
    opened_at: str


# ---------------------------------------------------------------------------- tools

@mcp.tool(annotations=READ_ONLY)
def search_services(query: str) -> list[ServiceSummary]:
    """Find services whose name, description, or owning team contains the query text.

    Use this first when the user mentions a service loosely, such as "the payments
    thing", to find its exact name.
    """
    return catalog_db.search_services(query)


@mcp.tool(annotations=READ_ONLY)
def get_service(name: str) -> Service:
    """Get one service's owner, on-call engineer, Slack channel, and dependencies.

    The name must be exact, for example "payments-api". The result lists both the
    services it depends on and the services that depend on it.
    """
    service = catalog_db.get_service(name)
    if service is None:
        # ToolError sends this message to the model so it can recover, usually by
        # calling search_services. Any other exception is treated as a crash, and the
        # SDK hides its text from the model in case it holds internal details.
        raise ToolError(f"No service named {name!r}. Try search_services first.")
    return service


@mcp.tool(annotations=READ_ONLY)
def list_open_incidents(service: str | None = None) -> list[Incident]:
    """List open incidents, most severe first. Leave service empty to see every service."""
    return catalog_db.list_incidents(service=service, status="open")


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False,
                                      open_world_hint=False))
def create_incident(service: str, title: str,
                    severity: Literal["sev1", "sev2", "sev3"]) -> Incident:
    """Open a new incident against a service.

    Only call this when the user has clearly asked to open an incident. sev1 means
    customers can't complete orders, sev2 means a feature is degraded, and sev3 is
    a minor issue with a workaround.
    """
    if catalog_db.get_service(service) is None:
        raise ToolError(f"No service named {service!r}. Try search_services first.")
    incident = catalog_db.create_incident(service, title, severity)
    # stdout carries the protocol on stdio, so diagnostics go to stderr. VS Code shows
    # stderr in the server's output log.
    print(f"created incident {incident['id']} for {service}", file=sys.stderr)
    return incident


# ------------------------------------------------------------------------ resources

@mcp.resource("catalog://teams", mime_type="text/markdown")
def teams() -> str:
    """Every team, its Slack channel, its on-call engineer, and the services it owns."""
    lines = ["# Teams", ""]
    for t in catalog_db.list_teams():
        lines.append(f"- **{t['name']}** ({t['channel']}), on call: {t['on_call']}. "
                     f"Owns: {t['services']}")
    return "\n".join(lines)


@mcp.resource("catalog://services/{name}/runbook", mime_type="text/markdown")
def runbook(name: str) -> str:
    """The incident runbook for one service."""
    text = catalog_db.get_runbook(name)
    if text is None:
        raise ResourceNotFoundError(f"No service named {name!r}.")
    return f"# Runbook: {name}\n\n{text}"


# -------------------------------------------------------------------------- prompts

@mcp.prompt()
def incident_briefing(service: str) -> str:
    """Prepare a short briefing for whoever is joining an incident on a service."""
    return (
        f"I'm joining an incident on {service}. Using the service catalog tools, give me "
        "a briefing with these sections: who owns it and who is on call, its open "
        "incidents, which services it depends on and which depend on it, and the first "
        "three steps from its runbook (resource "
        f"catalog://services/{service}/runbook). Keep it under 200 words."
    )


@mcp.prompt()
def team_onboarding(team: str) -> str:
    """Summarize what a new engineer on a team needs to know about its services."""
    return (
        f"I've just joined the {team} team. Using the service catalog, list the services "
        "we own, what each one does, its tier, and anything currently open against it. "
        "Finish with the two services I should learn first and why."
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
