# ws — Cross-Project Workspace CLI

**ws** is the Forge workspace CLI. It treats `~/Workspace` as a first-class entity: indexes git repos, tracks cross-project health, manages feature worktrees, shares context between projects, and exposes all operations as MCP tools for AI agents.

```bash
pipx install ws-cli
ws init
ws scan
ws status
```

## Why ws?

AI coding agents (Claude Code, Codex, Cursor) are powerful, but they start blind in every repo. ws gives them — and you — cross-project awareness:

- **See everything at once**: `ws status` shows all your repos with branch, dirty state, ahead/behind
- **Share context across projects**: `ws share "deploy: run migrations first" --group backend` — all agents in that group see it
- **Feature branches across repos**: `ws feature create "refactor-auth" --repos svc-a,svc-b` — creates git worktrees in one command
- **MCP for AI agents**: `ws serve` exposes 13 tools over stdio — any MCP-compatible agent calls them directly

## Quick Start

```bash
# Install
pipx install ws-cli

# Initialize
ws init --provider github

# Discover existing repos
ws scan

# See workspace status
ws status

# Check dev environment
ws health
```

## Commands

| Command | Description |
|---------|-------------|
| `ws init [--provider github]` | Initialize workspace config + auth |
| `ws scan` | Discover new git repos in ~/Workspace |
| `ws status [name] [--json]` | Show workspace/repo status |
| `ws health` | Check dev environment (brew, ollama, gh, disk) |
| `ws clone <url> [--name]` | Clone + register in workspace |
| `ws feature create <name> [--repos a,b]` | Create feature |
| `ws feature list` | List active features |
| `ws feature worktree <id> --repo <name>` | Create git worktree for feature |
| `ws share <content> [--group g]` | Share note across projects |
| `ws notes [group]` | List shared notes |
| `ws serve` | Start MCP stdio server |
| `ws config` | Show config path |

## MCP Server

Any MCP-compatible AI agent connects to ws via stdio:

```bash
# Terminal 1: Start MCP server
ws serve

# In your AI agent (Claude Code, Codex, etc.):
#   → ws serves 13 tools:
#     list_repos, repo_status, workspace_status, workspace_health,
#     clone_repo, workspace_scan, create_feature, list_features,
#     log_decision, get_decisions, start_session, share_note,
#     get_shared_notes
```

**Claude Code setup:**
```json
{
  "mcpServers": {
    "ws": {
      "command": "ws",
      "args": ["serve"]
    }
  }
}
```

## Architecture

```
Agent (Claude Code / Codex)
  │ MCP stdio
  ▼
ws serve ───→ 13 MCP tools
  │
ws CLI ─────→ init, status, clone, feature, share
  │
  ▼
subprocess: git, brew, gh, graphify
```

ws is the workspace infrastructure layer. It does not compete with AI agents — it gives them workspace superpowers.

## State

```
~/.workspace/
├── config.json       # Repos, groups, features, sessions
├── sessions/<id>/    # Agent session artifacts
│   ├── meta.json
│   └── transcript.md
└── .workspaces/      # Git worktrees for features
```

All state is plain JSON. No server, no daemon, no lock-in.

## Integration: graphify

```bash
# Install graphify
pipx install graphifyy

# Build a knowledge graph for any repo
cd ~/Workspace/my-project
/graphify .

# ws status provides machine-readable input for graphify
ws status --json | graphify extract --stdin  # (future)
```

## Contributing

```bash
git clone https://github.com/forge/ws-cli
cd ws-cli
pipx install -e .
```

See [ROADMAP.md](./ROADMAP.md) for the development plan.

## License

MIT
