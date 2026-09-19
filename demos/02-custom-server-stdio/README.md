# Demo 2: A Custom Server over stdio

Most teams start with MCP because they want an agent to reach something only they have, such as an internal API or database. In this demo you'll build exactly that: a Python MCP server that gives Copilot access to a company's service catalog, stored in SQLite. It uses all three MCP primitives, so you can see when each one fits.

## Before You Start

You'll need these installed:

- [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.12 or later
- [Node.js](https://nodejs.org/) 24, for the MCP Inspector
- [Visual Studio Code](https://code.visualstudio.com/) with [GitHub Copilot set up](https://code.visualstudio.com/docs/setup/copilot)

Open this folder as its own VS Code window, then open a terminal in it and install the Python dependencies:

```
uv sync
```

The Copilot steps are written for VS Code's Local agent harness. Recent VS Code builds can start new chats on the Copilot harness instead, which calls MCP tools but doesn't show MCP resources or prompts in the chat input, and handles tool approvals differently. If the controls under the chat input offer **Interactive**, **Plan**, and **Autopilot**, you're on the Copilot harness. Open Settings, search for `chat.editor.preferCopilotHarness`, turn it off, and select **New Chat**. The [demos overview](../README.md#check-which-agent-harness-youre-on) has more detail.

## What's in This Folder

| File | Purpose |
|------|---------|
| `catalog_db.py` | Builds, seeds, and queries the SQLite service catalog |
| `server.py` | The MCP server: four tools, two resources, and two prompts |
| `check_server.py` | A Python MCP client that exercises the server without Copilot |
| `.vscode/mcp.json` | Registers the server so Copilot starts it over stdio |

The database file, `data/catalog.db`, appears the first time the server runs. It isn't committed to the repo.

## Presentation Trail

#### Step 1: Look at the internal data

Open `catalog_db.py`. This stands in for whatever internal system you'd want to expose. It holds teams, the services they own, which services depend on which, and incidents.

- `connect` builds and seeds the database the first time it's needed, so there's no setup step and nothing binary in the repo.
- Every query uses `?` placeholders. The values will come from an AI model, so they're treated as untrusted input and never pasted into the SQL text. Demo 4 shows what happens when that rule is broken.

#### Step 2: Read the server

Open `server.py` and work down the file.

- **The server object.** `MCPServer` comes from the official SDK. In version 2 of the SDK it replaced the `FastMCP` class you'll see in older tutorials. The `instructions` text tells the host what the server is for.
- **Typed results.** `ServiceSummary`, `Service`, and `Incident` are `TypedDict` classes. Because the tools declare them as return types, each tool publishes an output schema, and its results arrive as structured JSON as well as text.
- **Tools.** `search_services`, `get_service`, and `list_open_incidents` are marked read-only in their annotations. `create_incident` isn't, because it writes to the database, and its `severity` argument is a `Literal`, so the model can only choose one of three values. The docstrings matter more than they look: they're the only guidance the model gets about when to call each tool.
- **Errors.** When a service name doesn't exist, the tool raises `ToolError`. The SDK sends that message to the model, which can then recover by searching. Any other exception is treated as a crash, and the SDK hides its details from the model in case they include something internal.
- **Logging.** `create_incident` prints to stderr, never stdout. On stdio, stdout carries the protocol, so a stray `print` would corrupt it.
- **Resources.** `catalog://teams` is a fixed resource, and `catalog://services/{name}/runbook` is a template that covers every service. Resources are context the user or host chooses to attach, rather than actions the model chooses to take.
- **Prompts.** `incident_briefing` and `team_onboarding` are reusable instructions with parameters. The user picks them, much like a saved query.
- **Running it.** `mcp.run(transport="stdio")` means a host starts this file as a child process and talks to it over stdin and stdout.

#### Step 3: Test it without an AI model

It's worth proving the server works before a model is involved, because a model will often work around a broken tool rather than report it. Run the check script:

```
uv run check_server.py
```

It starts `server.py` exactly as VS Code will, then lists each primitive and calls a few. Notice two results in particular. The `get_service` call returns structured JSON that matches the `Service` type. The call with a bad name returns the `ToolError` message, which is what the model will see.

#### Step 4: Explore it with the MCP Inspector

The MCP Inspector is the standard tool for poking at a server by hand. List the tools:

```
npx -y @modelcontextprotocol/inspector@2.10.1 --cli uv run server.py --method tools/list
```

Each tool shows its input schema, built from the type hints, and its output schema, built from the return type. Now call one:

```
npx -y @modelcontextprotocol/inspector@2.10.1 --cli uv run server.py --method tools/call --tool-name get_service --tool-arg name=checkout-web
```

#### Step 5: Connect it to Copilot

Open `.vscode/mcp.json`. There's one `stdio` server, and VS Code will run `uv run server.py` in this folder. Run **MCP: List Servers** from the Command Palette and start **service-catalog**. Then, in the Chat view, set **Session Target** to **Local** and pick the **Agent** role.

#### Step 6: Let the model choose the tools

Ask Copilot a question in plain language:

```text
Who's on call for the payments API, and is anything open against it right now?
```

Watch the sequence of tool calls. "The payments API" isn't an exact service name, so Copilot usually calls `search_services` first, then `get_service` and `list_open_incidents` with the exact name it found. You didn't write that plan. The tool descriptions made it possible.

#### Step 7: Attach a resource

Resources are chosen by you, not the model. In the Chat view, select **Add Context**, choose **MCP Resources**, and pick **catalog://teams**. The **MCP: Browse Resources** command does the same thing from the Command Palette. Then ask:

```text
Which team owns the most tier 1 services?
```

Copilot can answer from the attached resource alone, without calling a tool. Try the runbook template too. When you pick it, VS Code asks for the service name.

#### Step 8: Run a prompt

MCP prompts appear as slash commands in the Chat view, named after the server and the prompt. Type `/service-catalog.incident_briefing`, or pick it from the list that appears when you type `/`. Enter `checkout-web` when you're asked for the service, and send it.

The prompt's text tells Copilot which tools and resources to use and how to format the briefing, so every engineer gets the same structure.

#### Step 9: Make a change

Ask Copilot to write something:

```text
Open a sev3 incident for checkout-web: the cart count is wrong after removing items.
```

Because `create_incident` isn't marked read-only, Copilot shows you the exact arguments and waits for approval. Allow it, then ask Copilot to list the open incidents again to see the new one.

To put the sample data back the way it started:

```
uv run catalog_db.py --reset
```

## What You Saw

- A useful MCP server is a thin layer of typed Python functions over a system you already have.
- Tools are for the model to call, resources are context for the user to attach, and prompts are templates for the user to run.
- Descriptions, type hints, and annotations are the server's whole interface with the model, so they deserve the same care as an API design.
- Test the server directly before you test it through a model.
