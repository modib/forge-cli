# forge CLI Documentation

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)**

---

forge is the cross-project workspace CLI for [Forge OS](https://github.com/modib/forge). It manages git repos in `~/Workspace`, tracks dependencies and CVEs, shares context across projects, and exposes all operations as MCP tools for AI agents.

## Quick Links

- [Getting Started](./getting-started.md) — Install, init, first commands
- [Commands](./commands.md) — Full CLI reference
- [MCP Server](./mcp.md) — AI agent integration
- [Architecture](./architecture.md) — How it works
- [Schema](../SCHEMA.md) — State model reference
- [Roadmap](../ROADMAP.md) — Development plan

## What is forge?

- **Cross-project status**: One command shows all your repos — branch, dirty state, ahead/behind
- **Dependency intelligence**: Parse 6 lockfile formats across all repos; `forge cve list` shows known vulnerabilities
- **CVE scanning**: Query OSV.dev for vulnerabilities in your workspace dependencies
- **Feature management**: Create feature branches across multiple repos with git worktrees
- **Config management**: `forge config path` shows your active directory (`~/.forge/` or `~/.workspace/`); `forge config validate --fix` and `forge config remove-repo` keep it clean
- **Shared context**: Notes and decisions that span projects, visible to all AI agents
- **MCP server**: 24 tools over stdio — Claude Code, Codex, Gemini CLI, and any MCP agent can call them
- **AI-native**: `forge ai detect` probes hardware, `forge ai setup` installs Ollama or MLX with Gemma 4 models, `forge exec` routes natural language to forge commands

## Install

**Recommended — Homebrew:**

```bash
brew tap modib/forge
brew install forge-cli
```

**Alternative — pipx** (no Homebrew required):

```bash
pipx install forge-cli
```

Then:

```bash
forge init --provider github
forge config path    # shows active config directory (~/.forge/ or ~/.workspace/)
forge scan
forge status
```

## Project Status

forge CLI is in active development (v0.4.2 — CVE Scanning + Gemma 4). See the [roadmap](../ROADMAP.md) for what's coming.

---

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)**