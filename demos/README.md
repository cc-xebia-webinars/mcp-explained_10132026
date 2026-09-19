# Demos

These four demos follow the webinar agenda from the protocol itself to a custom server and the security questions you'll want answered before production. Each demo is self-contained, with its own `uv` project pinned to Python 3.14, so you can run any of them on its own. GitHub Copilot in Visual Studio Code is the MCP host throughout, and every server we write is Python built on the official MCP Python SDK.

| # | Demo | Description | Time |
|---|------|-------------|------|
| 1 | [Meet MCP](./01-meet-mcp/README.md) | The request/response lifecycle in raw JSON-RPC against both a legacy and a modern server, followed by three ready-made servers in Copilot: filesystem, GitHub, and Microsoft Learn. | 16 min |
| 2 | [A Custom Server over stdio](./02-custom-server-stdio/README.md) | A Python MCP server that exposes an internal SQLite service catalog through tools, resources, and prompts, tested with a script and the MCP Inspector, then used from Copilot. | 18 min |
| 3 | [The Same Server over Streamable HTTP](./03-streamable-http/README.md) | The Demo 2 server served from a URL instead of a child process, shared by Copilot and a second client, with DNS rebinding protection and a bearer token guarding it. | 16 min |
| 4 | [Security and Trust Boundaries](./04-security/README.md) | A server update that slips a poisoned instruction into a tool description, an audit that pins approved tools and catches the change, a file server scoped down to the folder it needs, a raw SQL tool next to a parameterized, read-only one, a prompt injection hidden in data, and a log of every call. | 20 min |

## Getting Ready

Every demo needs these tools:

- [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.12 or later. It installs Python 3.14 for you if you don't have it.
- [Node.js](https://nodejs.org/) 24. The MCP Inspector and the official filesystem server are Node packages, and `npx` runs them.
- [Visual Studio Code](https://code.visualstudio.com/) with [GitHub Copilot set up](https://code.visualstudio.com/docs/setup/copilot).

Demo 1 also needs a GitHub account, which you already have if you use Copilot.

Run `uv sync` in each demo folder while you're online, and run Demo 1's `lifecycle.py` once so `npx` caches the filesystem server. After that, everything runs offline except Copilot itself and the hosted GitHub and Microsoft Learn servers in Demo 1.

Open each demo as its own VS Code window, for example `code demos/02-custom-server-stdio`. VS Code reads MCP servers from `.vscode/mcp.json` at the root of the workspace, so opening the demo folder directly gives Copilot that demo's servers and nothing else.

In the Chat view, set **Session Target** to **Local** and pick the **Agent** role before you try any of the Copilot steps. The demos are written for the Local agent harness, which runs inside VS Code and supports everything MCP offers: tools, resources, prompts, and an approval prompt before a tool changes anything.

### Check Which Agent Harness You're On

VS Code has more than one agent harness, and recent builds can start new chats on the Copilot harness instead of Local. The Copilot harness runs in a separate process and manages MCP servers its own way. It still connects to the servers in `.vscode/mcp.json` and can call their tools, but it doesn't offer **MCP Resources** under **Add Context**, it doesn't list MCP prompts as slash commands, and its permission settings work differently. Several demo steps won't match what you see.

You're on the Copilot harness if the controls under the chat input offer the **Interactive**, **Plan**, and **Autopilot** modes. To switch back to Local:

1. Open Settings and search for `chat.editor.preferCopilotHarness`.
2. Turn the setting off.
3. Select **New Chat** at the top of the Chat view. A session that's already started keeps the harness it started with.

In a Local session, the role picker in the chat input offers **Ask**, **Agent**, and **Plan**, and the **Interactive** control is gone.

Demos 2, 3, and 4 build a small SQLite database the first time a server starts, in each demo's `data` folder. It's never committed. If a demo's data gets into a strange state, reseed it from that demo's folder:

```
uv run catalog_db.py --reset
```

## Using Another Host

The demos use GitHub Copilot in VS Code, but the servers are ordinary MCP servers, and any MCP host can run them. Only the configuration file changes. Here's the Demo 2 server registered in two other popular hosts.

[Claude Code](https://code.claude.com/docs/en/mcp) reads a `.mcp.json` file at the root of the project. Open the demo folder as the project, then add:

```json
{
  "mcpServers": {
    "service-catalog": {
      "command": "uv",
      "args": ["run", "server.py"]
    }
  }
}
```

[Cursor](https://cursor.com/docs/context/mcp) reads `.cursor/mcp.json` in the project, and supports `${workspaceFolder}`:

```json
{
  "mcpServers": {
    "service-catalog": {
      "command": "uv",
      "args": ["run", "--directory", "${workspaceFolder}", "server.py"]
    }
  }
}
```

The differences from VS Code's `.vscode/mcp.json` are small: the top-level key is `mcpServers` rather than `servers`, and HTTP servers are written with a `url`, plus `"type": "http"` in Claude Code. VS Code's `inputs` section, which Demo 3 uses to ask for a token, is specific to VS Code. Cursor can read a value from an environment variable with `${env:NAME}`, and other hosts have their own approaches, so check the host's documentation rather than writing a token into the file.
