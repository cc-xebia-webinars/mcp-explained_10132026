# Demo Instructions for This Webinar

The general rules for demos, including folder naming, `uv` setup, the README structure, and the writing style, are in the `CLAUDE.md` file at the root of the repo. This file adds what's specific to this webinar.

## Tools

- The AI tool is GitHub Copilot in Visual Studio Code. MCP servers are used from the Chat view with the **Local** session target and the **Agent** role, because only Local sessions use the servers in the workspace's `.vscode/mcp.json`.
- Python is the programming language for every MCP server and any supporting code. Build custom servers with the official MCP Python SDK (the `mcp` package on PyPI).
- Each demo pins Python 3.14 in its `pyproject.toml` and `.python-version` file.
- Node.js 24 is required for MCP tooling that ships as Node packages, such as the MCP Inspector and the official filesystem server, run through `npx`. Node is for tooling only; don't write demo code in JavaScript or TypeScript.
- Register each demo's MCP servers in a `.vscode/mcp.json` file inside that demo's folder, and have students open the demo folder as its own VS Code workspace so Copilot picks up that configuration and nothing else.

## Outside Services

These are the only services a demo may use beyond the presenter's machine. None of them needs a paid plan or an API key.

- GitHub Copilot, the AI tool for every demo.
- The GitHub MCP server, GitHub's hosted server, which VS Code signs in to with the student's GitHub account. Point it at a repository the student owns, and prefer read-only tools so the demo can't change anything by accident.
- The Microsoft Learn MCP server, which provides search over Microsoft's documentation and is the web search example for this webinar. It needs no sign-in.

Everything else, including the filesystem server, the custom server, and the sample database, runs locally.

## Coverage

Plan the demos so that, between them, they cover the following. How the topics group into demos is up to you, within the 20-minute limit for each demo.

- **Existing servers.** Show the filesystem, GitHub, and Microsoft Learn servers working from Copilot, and show how each one is registered in `.vscode/mcp.json`.
- **A custom server over stdio.** Build a minimal Python server that exposes internal data to Copilot through tools, resources, and prompts, so all three primitives appear. The internal data is a SQLite database that the demo creates and seeds at run time, accessed through Python's built-in `sqlite3` module. This custom server is the webinar's database example, so there's no separate existing database server; the slides mention that ready-made database servers exist.
- **The same custom server over Streamable HTTP.** Run the server from the stdio example over Streamable HTTP, and show what changes in the code and in `.vscode/mcp.json` and what stays the same. Bind it to `localhost` only.
- **Security.** Give security its own demo, built on local servers only. Show the risks from the agenda in action and how to guard against each one, such as a filesystem server given a wider root than it needs, a tool description that tries to steer the model, Copilot's tool approval prompts, limiting the GitHub server to read-only tools, and the difference between a database tool that runs any SQL the model writes and one that uses fixed, parameterized queries over a read-only connection. Keep every example harmless: a demo may show that an attack would work, but it must never send data anywhere or change anything outside the demo folder.
