"""The smallest useful MCP server: one tool, built with the official Python SDK.

It's here so lifecycle.py has a modern, stateless server to talk to next to the
legacy filesystem server. Demo 2 builds a real server the same way.

    uv run lifecycle.py hello
"""

from mcp.server import MCPServer

mcp = MCPServer("hello", version="1.0.0")


# The function name becomes the tool name, the type hints become its input schema,
# and the docstring becomes the description the model reads when choosing a tool.
@mcp.tool()
def say_hello(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}! This answer came back over MCP."


if __name__ == "__main__":
    mcp.run(transport="stdio")
