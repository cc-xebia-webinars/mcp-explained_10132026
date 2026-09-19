# MCP Server Review Checklist

Use this checklist before you connect an MCP server to a team's tools, and again whenever that server changes. It treats a server the way you'd treat any dependency that gets access to production systems, because that's what it is. The demos in this repository show most of these checks in action.

## Before You Connect a Server

- [ ] You know who publishes the server, and it comes from a source you'd accept for any other dependency.
- [ ] You've read the full description of every tool, the text the model sees, not just the tool names. Look for instructions to the model, references to credentials, or requests to keep something from the user.
- [ ] You've checked each tool's arguments for anything that doesn't fit its purpose, such as a free-text `notes` field on a unit converter.
- [ ] You've recorded what you approved, so a later change can be spotted. Fingerprinting each tool's description, arguments, and annotations is one way to do it.
- [ ] You don't rely on a server's tool annotations, such as read-only hints, as proof of anything. They're the server's own claim.

## Configuration and Least Privilege

- [ ] The server's version is pinned, for example `package@1.2.3` rather than an unversioned `npx` command, so it can't update without a decision.
- [ ] A file server can reach only the folder it needs, and you've checked what it can actually see, since some servers let the client's workspace roots replace the folder you configured.
- [ ] Tokens carry the fewest scopes that work, and hosted servers use read-only modes and narrow toolsets where they offer them.
- [ ] Secrets reach the server through the host's input prompts or a secret store, never written into a configuration file in the repository.
- [ ] Only the servers a task needs are switched on, and tools that aren't needed are turned off in the host.

## Designing Your Own Servers

- [ ] Each tool does one specific job. There's no raw SQL, shell, or HTTP tool that hands the model a blank cheque.
- [ ] Database queries use parameters, never values pasted into the SQL text, and read-only tools use a read-only connection.
- [ ] Paths from the model are resolved and checked against an allowed root before anything is opened.
- [ ] Tool descriptions say clearly what each tool does and when to use it, and nothing more.
- [ ] Anticipated errors return a clear message, and unexpected ones don't leak internal details to the model.
- [ ] On stdio, logs go to stderr, because stdout carries the protocol.

## HTTP Servers

- [ ] The server listens only where it has to, such as `127.0.0.1` on a laptop, and never on all interfaces by accident.
- [ ] `Host` and `Origin` headers are checked, to block DNS rebinding.
- [ ] Every request needs an access token, ideally issued through OAuth by your identity provider, and the server validates it.
- [ ] Traffic beyond the local machine uses TLS.

## Running in Production

- [ ] Tool approvals stay on for anything that writes, deletes, or sends data, and the people approving calls read the arguments.
- [ ] Every tool call on the servers you own is logged with its time, tool, arguments, and outcome.
- [ ] You assume that any text a tool returns, such as an issue, a document, or a web page, may contain instructions, and you don't place risky tools next to tools that read untrusted content.
- [ ] Someone owns each server's review, and it's repeated whenever the server or its configuration changes.
- [ ] You follow the MCP specification's changelog, because the protocol and its security guidance are still moving.
