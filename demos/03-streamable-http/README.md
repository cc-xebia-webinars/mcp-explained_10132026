# Demo 3: The Same Server over Streamable HTTP

The server from Demo 2 runs as a child process that VS Code starts for you. That works well on one laptop, but it means every user runs their own copy. In this demo you'll serve the same server over Streamable HTTP, so it becomes a long-running service at a URL that any number of clients can share. You'll also see two of the protections an HTTP server needs and a stdio server doesn't: checking where requests come from, and requiring a token.

## Before You Start

You'll need these installed:

- [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.12 or later
- [Visual Studio Code](https://code.visualstudio.com/) with [GitHub Copilot set up](https://code.visualstudio.com/docs/setup/copilot)

Open this folder as its own VS Code window, then open a terminal in it and install the Python dependencies:

```
uv sync
```

The Copilot steps are written for VS Code's Local agent harness. Recent VS Code builds can start new chats on the Copilot harness instead, which calls MCP tools but doesn't show MCP resources or prompts in the chat input, and handles tool approvals differently. If the controls under the chat input offer **Interactive**, **Plan**, and **Autopilot**, you're on the Copilot harness. Open Settings, search for `chat.editor.preferCopilotHarness`, turn it off, and select **New Chat**. The [demos overview](../README.md#check-which-agent-harness-youre-on) has more detail.

## What's in This Folder

| File | Purpose |
|------|---------|
| `catalog_db.py` | The same service catalog database as Demo 2 |
| `server.py` | The same MCP server as Demo 2, unchanged |
| `http_server.py` | Serves `server.py` over Streamable HTTP |
| `http_client.py` | A second client that shares the running server with Copilot |
| `rebinding_check.py` | Sends honest and forged requests to show DNS rebinding protection |
| `secure_http_server.py` | The same server again, turning away any request without a bearer token |
| `auth_check.py` | Sends requests with no token, a wrong token, and the right one |
| `.vscode/mcp.json` | Points Copilot at both servers' URLs, and prompts for the secure server's token |

## Presentation Trail

#### Step 1: Confirm the server didn't change

The tools, resources, and prompts are transport-independent, so `server.py` is a straight copy of the file from Demo 2. You can check that with git, which prints nothing when two files are identical:

```
git diff --no-index ../02-custom-server-stdio/server.py server.py
```

#### Step 2: Read the HTTP entry point

Open `http_server.py`. It imports the same `mcp` object and calls `run` with a different transport. That's the only code change.

- `transport="streamable-http"` serves MCP from a single endpoint, `/mcp`. Clients send each JSON-RPC message as an HTTP POST, and the server can answer with plain JSON or stream several messages back.
- `HOST = "127.0.0.1"` keeps the server reachable from this machine only. Binding to `0.0.0.0` would put an unauthenticated server, with a tool that writes to the database, on every network the laptop joins. Step 8 adds authentication.
- Because the host is a loopback address, the SDK switches on DNS rebinding protection by itself. You'll test that in step 7.

#### Step 3: Start the server

In the terminal, start the server and leave it running:

```
uv run http_server.py
```

Notice that you start it yourself this time. With stdio, the host owns the server's lifetime. Over HTTP, the server has a life of its own.

#### Step 4: Point Copilot at the URL

Open `.vscode/mcp.json`. Compare the **service-catalog** entry with Demo 2's: there's no `command` or `args`, just `"type": "http"` and a `url`. Ignore **service-catalog-secure** for now; it's for step 8. Run **MCP: List Servers** from the Command Palette, start **service-catalog**, and in the Chat view set **Session Target** to **Local** and pick the **Agent** role. Then ask:

```text
List the open incidents, most severe first.
```

The tool calls look exactly as they did in Demo 2. Copilot can't tell, and doesn't need to know, how the server is reached. In the server's terminal, each call shows up as a `POST /mcp` line.

#### Step 5: Share the server with a second client

Open `http_client.py`. It connects to the same URL with the SDK's `Client` class, opens an incident, and lists what's open.

Open a second terminal in this folder, and run it while the server is still running:

```
uv run http_client.py
```

The client reports the protocol version it agreed with the server, which is the stateless `2026-07-28` revision. Now ask Copilot again:

```text
List the open incidents again. Is there anything new?
```

The incident the script opened appears in Copilot's answer, because both clients share one server and one database. With stdio, each host would have its own server process, and the two would only meet in the database file.

#### Step 6: Notice what stateless buys you

Under the 2026-07-28 protocol, there's no session to set up and no session ID to track. Each POST carries everything the server needs, including the protocol version. That's why HTTP servers can now sit behind an ordinary load balancer and scale out like any other stateless web service.

#### Step 7: See DNS rebinding protection

Open `rebinding_check.py`. A DNS rebinding attack tricks your browser into sending requests to a server on `127.0.0.1` while the web page thinks it's talking to its own public site. The forged request still names that site in its `Host` and `Origin` headers, and that's what gives it away.

With the server still running, run the check from your second terminal:

```
uv run rebinding_check.py
```

The honest request gets `200 OK`. The forged one gets `421 Misdirected Request` with `Invalid Host header`, and it never reaches the MCP layer. If you bind to another address or put the server behind a proxy, you configure this yourself with the `transport_security` argument, and you shouldn't switch it off.

#### Step 8: Require a token

Everything so far trusts anyone who can reach the port. Open `secure_http_server.py`. It serves the same `mcp` object, but wraps it in a small piece of middleware that checks every HTTP request for an `Authorization: Bearer` header and returns `401 Unauthorized` without one. The check happens before MCP sees the request. It runs on its own port, 8766, so you can keep the first server running.

In your second terminal, start it:

```
uv run secure_http_server.py
```

It prints a random token when it starts. Copy it. Open a third terminal in this folder and check how the server treats requests, replacing `<token>` with the one you copied:

```
uv run auth_check.py <token>
```

No token and a wrong token both get `401`. Only the printed token gets through.

Now look at the **service-catalog-secure** entry in `.vscode/mcp.json`. Its `headers` block sends `Authorization: Bearer ${input:catalog-token}`, and the `inputs` section at the top tells VS Code to ask for that value as a password, so the token never sits in a file. In **MCP: List Servers**, stop **service-catalog** and start **service-catalog-secure**. Paste the token when VS Code asks, then ask Copilot:

```text
List the open incidents again.
```

It works as before, because VS Code now sends the token with every request. A shared token is a stand-in for the real thing. In production, MCP uses OAuth: VS Code signs the user in with your identity provider and sends a short-lived access token, and the SDK checks it through `MCPServer`'s `token_verifier` and `auth` settings. GitHub's server in Demo 1 works exactly that way.

#### Step 9: Clean up

Stop both servers with Ctrl+C in their terminals. To remove the incidents the demo opened, reseed the database:

```
uv run catalog_db.py --reset
```

## What You Saw

- The same server code runs over stdio or Streamable HTTP. Only the `run` call and the host configuration change.
- Over HTTP, one running server can serve many clients, and the 2026-07-28 protocol makes it stateless.
- An HTTP server brings web security concerns with it: bind narrowly, check `Host` and `Origin`, and require a token, ideally from OAuth, before anyone else can reach it.
