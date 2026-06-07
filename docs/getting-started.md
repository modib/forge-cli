# Getting Started

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)**

---

## Prerequisites

- [Homebrew](https://brew.sh) (recommended) or [pipx](https://pipx.pypa.io) for installation
- Python 3.10+
- git 2.20+
- (optional) [gh CLI](https://cli.github.com) for GitHub auth
- (optional) [Ollama](https://ollama.ai) for local AI

## Install

**Recommended — Homebrew:**

```bash
brew tap modib/forge
brew install forge-cli
```

**Alternative — pipx** (works on any system, doesn't require Homebrew):

```bash
pipx install forge-cli
```

Verify:

```bash
forge --version
# forge 0.4.2
```

## Initialize

```bash
forge init --provider github
```

This creates `~/.forge/config.json` (backward-compatible with `~/.workspace`), checks GitHub auth (via `gh` CLI), and registers your GitHub username.

```
Initialized workspace at /home/user/.forge
Workspace root: /home/user/Workspace
Providers: github, gitlab
```

## Discover Repos

```bash
forge scan
```

This finds all git repositories in `~/Workspace`, registers them, and parses their dependencies.

```
Scanned 12 repos in /home/user/Workspace
Added 8 new repos:
  + my-project
  + another-project
  + docs
  ...
Parsed 142 dependencies across 12 repos
```

## Check Status

```bash
forge status
```

Shows all registered repos with branch, dirty state, and ahead/behind:

```
Workspace: /home/user/Workspace
Repos: 12 total
  (2 dirty, 1 ahead, 3 behind)

  my-project ●  main +2/-1
    fix: resolve auth token refresh race
  another-project  main
    docs: update API reference
  docs  master -3
    Merge pull request #42 from user/fix-typo
  ...
```

## Machine-Readable Output

```bash
forge status --json
```

Returns the full status as JSON — useful for scripts, AI agents, and pipeline integration.

## Check Dev Environment

```bash
forge health
```

```
Dev Environment Health
---------------------
  ✓ brew
  ✗ ollama
  ✓ gh
  ✓ python3
  ✓ node
  ✓ npm
  ✓ gh auth

Disk: 28.8% used (150.7 GB free of 228.0 GB)
```

## Scan for Vulnerabilities

```bash
# Refresh CVE data from OSV.dev
forge cve refresh

# List all known CVEs
forge cve list

# Security report
forge cve report
```

## List Dependencies

```bash
# All deps across all projects
forge deps list

# Filter by ecosystem
forge deps list --ecosystem pypi

# Per-repo
forge deps list --name my-project
```

## Connect AI Agents

```bash
forge serve
```

Starts the MCP stdio server with 24 tools. See the [MCP documentation](./mcp.md) for agent setup.

---

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)**