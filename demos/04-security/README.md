# Demo 4: Security and Trust Boundaries

Every MCP server you connect gets to put text in front of the model and run code on your behalf. In this demo you'll see four ways that goes wrong, and the guard for each one: a server whose update quietly adds instructions to steal a file, a server that can see more than it should, a database tool that runs whatever SQL the model writes, and instructions hidden in the data a safe tool returns. You'll finish by reading the log of every call that ran. Everything runs locally, and every "attack" is harmless by design. Nothing is sent anywhere, and nothing outside this folder changes.

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
| `poisoned_server.py` | A unit converter that's honest in release 1.0 and poisoned in release 1.1 |
| `files_server.py` | A file server limited to the root folder it's given at startup, with every call logged |
| `db_server.py` | A raw SQL tool next to a parameterized, read-only one, with every call logged |
| `audit_tools.py` | Prints every tool description the model will see, flags warning signs, and pins approved tools |
| `catalog_db.py` | The service catalog database from Demos 2 and 3, plus one incident whose title carries a prompt injection |
| `call_log.py` | Middleware that records every tool call to `data/tool-calls.log` |
| `shared-docs/` | Documents the file server is meant to share |
| `private/fake-credentials.txt` | Fake secrets, standing in for the `.env` files real projects contain |
| `.vscode/mcp.json` | Registers the three servers, with the file server's root set too wide |

## Presentation Trail

### Part 1: A server that changes after you approve it

#### Step 1: Start the servers

Open `.vscode/mcp.json`. It registers three local servers. Notice two things. The **files** server's root is `${workspaceFolder}`, the whole demo folder, including `private`, which is the kind of shortcut people take when they just want something to work. And the **unit-converter** server gets `CONVERTER_RELEASE` set to `1.0` in its `env` block.

Run **MCP: List Servers** from the Command Palette and start all three. In the Chat view, set **Session Target** to **Local** and pick the **Agent** role.

#### Step 2: Audit the servers and approve them

Open `audit_tools.py`. It reads the same `.vscode/mcp.json` that VS Code reads, starts each local server, and prints every tool description in full, because that's what the model reads and you usually don't. It flags phrases that have no business in an honest description. With `--approve`, it also records a fingerprint of each tool, covering its description, arguments, and annotations. Run it:

```
uv run audit_tools.py --approve
```

Read through the output. The converter's description is a single honest sentence, and the only warning is that `run_sql` can change data, which we'll come back to. Everything looks fine, so the fingerprints are saved to `approved-tools.json`. This is the review most teams do once, when they first add a server.

#### Step 3: Let the server update

In `.vscode/mcp.json`, change the converter's `CONVERTER_RELEASE` from `1.0` to `1.1`, and save. Restart **unit-converter** from **MCP: List Servers**.

This stands in for something that happens all the time: a server configured without a pinned version, such as an `npx` command with no version number, quietly picks up a new release the next time it starts. Nobody reviews it, because nobody notices.

#### Step 4: Ask an innocent question

Ask Copilot:

```text
Convert 42 km to miles.
```

Watch the tool calls carefully, and don't approve anything yet. Depending on the model, Copilot may try to call **read_file** on `private/fake-credentials.txt` first, or call **convert_units** with the file's contents in a `notes` argument. Nothing in your question asked for that.

If it does, expand the confirmation to see the arguments, and deny the call. If Copilot ignores the hidden instruction, that's the model's safety training doing its job, but it isn't something to rely on. Either way, the next step shows the instruction is there.

#### Step 5: Find the hidden instruction

Open `poisoned_server.py`. Release 1.1 keeps the same tool and the same arguments, but its description now contains an `<IMPORTANT>` block telling the model to read the credentials file, pass it in `notes`, and not mention it to you. This is tool poisoning, and it works because models treat tool descriptions as trusted guidance.

Notice too that both releases mark the tool as read-only in their annotations. Annotations are the server's own claim about itself, and nothing checks them.

The server only prints what it receives to its own stderr. A real attacker would send it somewhere. If you allowed the calls, run **MCP: List Servers**, choose **unit-converter**, and select **Show Output** to see what would have leaked.

#### Step 6: Catch the change

Run the audit again, this time without `--approve`:

```
uv run audit_tools.py
```

The `convert_units` tool now has a new fingerprint and a `CHANGED` line saying it differs from what you approved, along with four warnings about its description. Treat an MCP server like a dependency: pin its version, review what it tells the model, and review it again whenever it changes.

### Part 2: Least privilege

#### Step 7: See what an over-broad root exposes

Ask Copilot:

```text
Using the files server, list the files you can read and tell me whether any of them look sensitive.
```

The list includes `private/fake-credentials.txt`, along with the Python files and everything else in the folder. Whatever a server can reach, a poisoned tool or a poisoned document can ask the model to fetch.

#### Step 8: Scope the server down

Open `files_server.py` and find `inside_root`. It resolves the requested path, which expands `..` and follows links, and refuses anything that lands outside the root. That check is only as good as the root you give it.

In `.vscode/mcp.json`, change the files server's root from `${workspaceFolder}` to `${workspaceFolder}/shared-docs`, and save. Restart the **files** server from **MCP: List Servers**, then ask:

```text
Using the files server, read ../private/fake-credentials.txt.
```

The tool refuses, because the path resolves outside `shared-docs`. Ask Copilot to convert 42 km to miles again. Even if the poisoned instruction is followed, the read fails, so there's nothing to leak. That's defense in depth: the audit might miss something, but the scoping still holds.

This is also why Demo 1's filesystem server deserved a second look. It lets the client's roots replace the folder you configured, so check what a ready-made server can actually reach, not just what you passed it.

### Part 3: Database access

#### Step 9: Give the model raw SQL

Open `db_server.py`. `run_sql` passes whatever SQL it's given straight to a read-write connection. Ask Copilot:

```text
Using the incidents database, delete all resolved incidents.
```

The confirmation shows the exact `DELETE` statement Copilot wants to run. In a real system, this is the moment a well-meant cleanup or a poisoned instruction becomes data loss. Allow it, since this is a local demo database, and Copilot reports how many rows it removed.

#### Step 10: Use the safer tool

Look at `incidents_for_service` in the same file. It answers one question with a fixed query, the model only supplies a value, and the connection opens with `mode=ro`, so SQLite itself refuses writes. Try to break it:

```text
Use incidents_for_service with the service name: x' OR '1'='1
```

The result is an empty list. The `?` placeholder sends the value separately from the SQL, so the quote characters are just part of an odd service name that matches nothing.

#### Step 11: Injection through data

A safe tool can still return dangerous text. Anyone who can file an incident controls its title, and the model reads every word. Ask Copilot:

```text
Summarize the open incidents for checkout-web.
```

Copilot calls `incidents_for_service`, which is read-only and can't be subverted. But one incident's title says it's a duplicate and tells AI assistants to run `DELETE FROM incidents WHERE service = 'checkout-web'` through `run_sql`, without telling you. If Copilot tries it, the confirmation shows the `DELETE`, and you deny it. If it doesn't, point at the title in the result anyway.

This is prompt injection, and it's the same trick as tool poisoning, arriving through data instead of a description. The safe tool did its job. The danger is that a riskier tool was sitting next to it. The real fix is not to offer `run_sql` at all, and to keep approvals on for anything that writes.

### Part 4: Keeping a record

#### Step 12: Review what ran

Open `call_log.py`. It's a small piece of middleware, attached to the files and database servers through the `middleware` argument of `MCPServer`, that writes one line of JSON for every tool call: when it happened, which tool ran, the exact arguments, and whether it failed. Now open `data/tool-calls.log`.

Every call from this demo is there, including the `DELETE` you approved in step 9 and the read of `../private/fake-credentials.txt` that the scoped server refused. When something goes wrong in production, this is how you find out what the model actually did. Notice that the unit converter isn't logged. You can only trust the logs of servers you control, so for third-party servers, logging belongs in the host or a proxy in front of them.

Put the sample data back when you're done:

```
uv run catalog_db.py --reset
```

To run the demo again from the start, set `CONVERTER_RELEASE` back to `1.0` and the files server's root back to `${workspaceFolder}` in `.vscode/mcp.json`, and delete `approved-tools.json` and `data/tool-calls.log`.

## What You Saw

- Tool descriptions are part of the attack surface. Pin server versions, review what each server tells the model, and review it again when it changes.
- Give each server the narrowest root, the fewest tools, and read-only access wherever you can, as Demo 1 did with GitHub's read-only endpoint.
- Prefer specific, parameterized tools over general ones like raw SQL, and enforce limits in the connection as well as the code.
- Text a tool returns can carry instructions too, so don't put a risky tool next to a safe one.
- Keep tool approvals switched on for anything that writes, and read the arguments before you allow a call.
- Log every call on the servers you own, so you can see what the model actually did.
