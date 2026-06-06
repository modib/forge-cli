# ws CLI Documentation

ws is the cross-project workspace CLI for [Forge](https://github.com/forge/forge). It manages git repos in `~/Workspace`, shares context across projects, and exposes all operations as MCP tools for AI agents.

## Quick Links

- [Getting Started](./getting-started.md) — Install, init, first commands
- [Commands](./commands.md) — Full CLI reference
- [MCP Server](./mcp.md) — AI agent integration
- [Architecture](./architecture.md) — How it works
- [Schema](../SCHEMA.md) — State model reference
- [Roadmap](../ROADMAP.md) — Development plan

## What is ws?

- **Cross-project status**: One command shows all your repos — branch, dirty state, ahead/behind
- **Feature management**: Create feature branches across multiple repos with git worktrees
- **Shared context**: Notes and decisions that span projects, visible to all AI agents
- **MCP server**: 13 tools over stdio — Claude Code, Codex, Gemini CLI, and any MCP agent can call them
- **AI-ready**: `ws exec` (coming in v0.3) uses a local 3B model for natural language workspace commands

## Install

```bash
pipx install ws-cli
```

Then:

```bash
ws init --provider github
ws scan
ws status
```

## Project Status

ws CLI is in active development (v0.1). See the [roadmap](../ROADMAP.md) for what's coming.
