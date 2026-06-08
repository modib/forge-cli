# forge CLI Documentation

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)** · **[Comparison](./comparison.md)**

---

> **`gh` and GitHub MCP Server talk to GitHub's API. Forge talks to your local workspace — all repos, git state, dependencies, CVEs, agent sessions, and shared decisions — and runs offline on old 8GB laptops with zero cloud dependencies.**

## Quick Links

- [Getting Started](./getting-started.md) — Install, init, first commands
- [Commands](./commands.md) — Full CLI reference
- [MCP Server](./mcp.md) — AI agent integration
- [Architecture](./architecture.md) — How it works
- [Comparison](./comparison.md) — Forge vs GitHub CLI vs GitHub MCP Server
- [Schema](../SCHEMA.md) — State model reference
- [Roadmap](../ROADMAP.md) — Development plan

## What is forge?

- **Cross-project status**: One command shows all your repos — branch, dirty state, ahead/behind
- **Dependency intelligence**: Parse 6 lockfile formats across all repos; `forge cve list` shows known vulnerabilities
- **CVE scanning**: Query OSV.dev for vulnerabilities; `forge cve fix <id>` shows safe upgrade versions
- **Semantic search**: `forge ask` — RAG across READMEs, deps, and CVEs using nomic-embed-text + Gemma 4
- **Agent sessions**: `forge sessions search "decision about auth"` — full-text search across session transcripts
- **Agent handoff**: `forge agent handoff <session-id> --to codex` — packages transcript + decisions for the next agent
- **Feature management**: Create feature branches across multiple repos with git worktrees
- **Config management**: `forge config path` shows your active directory; `forge config validate --fix` keeps it clean
- **Shared context**: Notes and decisions that span projects, visible to all AI agents
- **MCP server**: 26 tools over stdio — Claude Code, Codex, Gemini CLI, and any MCP agent can call them
- **AI-native**: `forge ai detect` probes hardware, `forge ai setup` installs Ollama with Gemma 4; `forge exec` routes natural language to forge commands

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

forge CLI is in active development (v0.5.0 — Agent Handoff, Sessions Search/Diff, CVE Fix). See the [roadmap](../ROADMAP.md) for what's coming.

---

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)** · **[Comparison](./comparison.md)**
