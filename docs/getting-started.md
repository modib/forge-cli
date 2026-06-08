# Getting Started

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)** · **[Comparison](./comparison.md)**

---

## Install

**Recommended — Homebrew:**

```bash
brew tap modib/forge
brew install forge-cli
```

**Alternative — pipx:**

```bash
pipx install forge-cli
```

## Initialize

```bash
# This creates ~/.forge/ with default config and discovers repos in ~/Workspace:
forge init --provider github

# See where your config lives:
forge config path

# The default workspace root is ~/Workspace — set yours:
forge config workspace-root /path/to/projects
```

## Daily Workflow

```bash
# 1. Scan for new repos (also installs AI + pulls nomic-embed-text):
forge scan

# 2. See what's happening:
forge status

# 3. Parse all dependencies:
forge deps list

# 4. Check for CVEs:
forge cve refresh   # query OSV.dev for all known deps
forge cve list      # show CVEs
forge cve report    # full CVE report

# 5. Get fix info for a specific vulnerability
forge cve fix CVE-2024-XXXXX   # shows safe upgrade path

# 6. Search workspace with natural language:
forge ask "what packages use lodash?"

# 7. Execute commands with natural language:
forge exec "show dirty repos"

# 8. Manage features:
forge feature create "refactor-auth" --repos frontend,api
forge decision "renamed User model to Account" --breaking

# 9. Start AI agent session:
forge exec "start session for auth refactor"

# 10. Hand off session context to another agent:
forge agent handoff <session-id> --to codex

# 11. Search past agent sessions:
forge sessions search "auth"

# 12. Start MCP server for AI agent integration:
forge serve
```

## What's New in v0.5.0

| Feature | Description |
|---------|-------------|
| `forge cve fix <id>` | Get fix versions, affected repos/lockfiles, and upgrade paths for CVEs |
| `forge agent handoff <id> --to <agent>` | Package sessions into handoff documents for other agents |
| `forge sessions search <query>` | Full-text search across session transcripts and metadata |
| `forge sessions diff <a> <b>` | Structured diff between two agent sessions |
| 2 new MCP tools | `cve_fix_info` + `agent_handoff` (26 total) |
| 1 new intent | `cve_fix` added to exec intent map (23 total) |

## Verify Setup

```bash
forge status          # shows all repos, branch, dirty state
forge health          # checks brew, ollama, gh, python, node
```

If `forge init` can't find repos in `~/Workspace`, set a custom root:

```bash
forge config workspace-root /your/projects/path
forge scan            # re-scan with updated root
```

## Next Steps

- [Commands Reference](./commands.md) — Full CLI documentation
- [MCP Server Setup](./mcp.md) — Connect AI agents to your workspace
- [Architecture Overview](./architecture.md) — How forge works under the hood
- [Comparison](./comparison.md) — Forge vs GitHub CLI vs GitHub MCP Server

---

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)** · **[Comparison](./comparison.md)**
