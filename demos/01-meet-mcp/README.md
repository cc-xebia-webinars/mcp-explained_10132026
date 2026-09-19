# Demo 1: Meet MCP

In this demo you'll see MCP from two angles. First, you'll watch the protocol itself by sending raw JSON-RPC messages to two servers, one from each era of the protocol. Then you'll connect three ready-made servers to GitHub Copilot and use them together in one conversation.

## Before You Start

You'll need these installed:

- [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.12 or later
- [Node.js](https://nodejs.org/) 24
- [Visual Studio Code](https://code.visualstudio.com/) with [GitHub Copilot set up](https://code.visualstudio.com/docs/setup/copilot)
- A GitHub account, for the GitHub MCP server

Open this folder as its own VS Code window, then open a terminal in it and install the Python dependencies:

```
uv sync
```

The Copilot steps are written for VS Code's Local agent harness. Recent VS Code builds can start new chats on the Copilot harness instead, which calls MCP tools but doesn't show MCP resources or prompts in the chat input, and handles tool approvals differently. If the controls under the chat input offer **Interactive**, **Plan**, and **Autopilot**, you're on the Copilot harness. Open Settings, search for `chat.editor.preferCopilotHarness`, turn it off, and select **New Chat**. The [demos overview](../README.md#check-which-agent-harness-youre-on) has more detail.

## What's in This Folder

| File | Purpose |
|------|---------|
| `lifecycle.py` | A hand-written MCP client that prints every JSON-RPC message it sends and receives |
| `hello_server.py` | A one-tool MCP server built with the official Python SDK |
| `notes/` | A few team documents for the filesystem server to read |
| `.vscode/mcp.json` | The filesystem, GitHub, and Microsoft Learn servers, registered for Copilot |

## Presentation Trail

### Part 1: The protocol on the wire

#### Step 1: Read the hand-written client

Open `lifecycle.py`. Real hosts use an SDK and never show you the messages, so this client builds each one by hand.

- `SERVERS` defines the two servers we'll talk to. The filesystem server is the official TypeScript one from npm, pinned to an exact version and pointed at the `notes` folder. The hello server is the small Python file next to this one.
- `StdioConnection` starts the server as a child process. Over stdio, every message is one line of JSON written to the server's stdin, and every reply is one line read from its stdout. The server's stderr is set aside, because that's where servers write their logs.
- `request` sends a message with an `id` and waits for the reply with the same `id`. `notify` sends a message with no `id`, and the server never answers it.
- `main` runs the lifecycle in order: probe, handshake if needed, discover the tools, call one, and shut down. The `--step` option makes `step` wait for Enter before each phase.

#### Step 2: Talk to a legacy server

Run the client against the filesystem server. The `--step` option pauses before each phase, so press Enter when you're ready for the next one. The first run downloads the server with `npx`, so give it a moment.

```
uv run lifecycle.py filesystem --step
```

Walk through the output section by section:

1. **Probe.** The client sends `server/discover` with a `_meta` block that carries the protocol version `2026-07-28`. The filesystem server replies with error `-32601`, which means "method not found." That tells the client it's a legacy server.
2. **Handshake.** The client falls back to `initialize`, offering version `2025-11-25`. The server answers with the version it accepts, its capabilities, and its name, and the client confirms with the `notifications/initialized` notification. From here on, the server remembers this conversation.
3. **Discovery.** `tools/list` returns fourteen tools. The output is trimmed, but notice that each tool has a name and a description. The description is what an AI model reads when it decides which tool to use.
4. **Invocation.** `tools/call` runs `list_directory` on the `notes` folder and returns the three file names as content.
5. **Shutdown.** On stdio there's no goodbye message. The client closes the server's input and the server exits.

#### Step 3: Read the smallest possible server

Open `hello_server.py`. It's about ten lines long. `MCPServer` comes from the official SDK, and the `@mcp.tool()` decorator turns an ordinary function into an MCP tool. The function name becomes the tool name, the type hints become the input schema, and the docstring becomes the description the model reads.

#### Step 4: Talk to a modern server

Run the same client against the hello server:

```
uv run lifecycle.py hello --step
```

This time the probe succeeds, and the lifecycle is shorter. Look for these differences:

- There's no `initialize` and no `notifications/initialized`. The 2026-07-28 protocol is stateless, so every request carries its protocol version and client details in `_meta` instead.
- The `server/discover` result lists the versions and capabilities the server supports.
- Every result has a `resultType` of `complete`, and list results carry `ttlMs` and `cacheScope` so clients know how long they can cache them.
- The server identifies itself in each result's `_meta` rather than once at the start.

Both eras are in use today. The official filesystem server still uses the handshake, while servers built with the current Python SDK speak both. A good client probes, as this one does, and adapts.

### Part 2: Ready-made servers in Copilot

#### Step 5: Read the server configuration

Open `.vscode/mcp.json`. This is where VS Code looks for a workspace's MCP servers, and it registers three of them:

- **filesystem** is a `stdio` server. VS Code runs `npx` with the exact package version, and passes `${workspaceFolder}/notes` as the folder the server may read. Pinning the version means nobody's server changes underneath them without a decision.
- **github** is an `http` server hosted by GitHub. The `/readonly` path asks it to offer only tools that read, so nothing in this demo can change a repository. VS Code signs in with your GitHub account, so there's no token to paste.
- **microsoft-learn** is an `http` server hosted by Microsoft that searches its official documentation. It needs no sign-in at all.

#### Step 6: Start the servers

Open the Command Palette and run **MCP: List Servers**. Start each of the three servers. The first time a server starts, VS Code asks whether you trust it, and the GitHub server asks you to sign in.

In the Chat view, set **Session Target** to **Local** and pick the **Agent** role. Then select **Configure Tools** in the chat input. You'll see each server's tools listed under its name, and you can switch tools on or off one at a time.

#### Step 7: Use the filesystem server

Ask Copilot:

```text
Using the filesystem tools, summarize the release checklist in the notes folder.
```

Copilot asks before it calls each tool. Expand the confirmation to see the tool name and the exact arguments it's about to send, then allow it.

Next, ask:

```text
Which directories is the filesystem server allowed to access?
```

The answer may surprise you. VS Code shares its workspace folders with servers as MCP *roots*, and this server replaces the folder in its command line with the roots the client sends. So it can see the whole demo folder, not just `notes`. Roots are deprecated in the 2026-07-28 protocol for reasons like this one, and Demo 4 comes back to it.

#### Step 8: Use the GitHub server

Ask Copilot about one of your own repositories, replacing the placeholder with a real one:

```text
Show me the five most recent open issues in <owner>/<repo>.
```

Then ask it to change something:

```text
Create an issue in <owner>/<repo> titled "Test from the MCP demo".
```

Copilot can't do it. The read-only endpoint never offered a tool for creating issues, so there's nothing for the model to call.

> Note, VS Code has a built-in GitHub MCP which will create issues if you are logged in which bypasses the read-only limitation mentioned above.

#### Step 9: Use the Microsoft Learn server

Ask Copilot:

```text
Search Microsoft Learn for how to roll back to a previous revision in Azure Container Apps.
```

The answer comes from Microsoft's current documentation rather than the model's training data, and Copilot usually links to the pages it used.

#### Step 10: Combine all three

Here's where MCP pays off. One request can now draw on your local files, your GitHub data, and up-to-date documentation:

```text
Read step 7 of the release checklist in the notes folder, then use Microsoft Learn to find the exact Azure CLI command for that step.
```

Watch the order of the tool calls. Copilot reads the file first, then searches the documentation using what it found. Neither server knows the other exists. The host is what connects them.

## What You Saw

- Every MCP conversation is JSON-RPC messages: discover or initialize, list, call, and shut down.
- Legacy servers use an `initialize` handshake, and modern servers carry the version on every request.
- A host connects to many servers at once, and the model chooses among all their tools.
- Configuration choices, such as pinned versions and read-only endpoints, are your first line of defense.
