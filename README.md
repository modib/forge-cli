# forge — Cross-Project Workspace CLI

**forge** is the Forge workspace CLI. It treats `~/Workspace` as a first-class entity: indexes git repos, tracks cross-project health, manages feature worktrees, shares context between projects, and exposes all operations as MCP tools for AI agents.

```bash
brew install modib/forge/forge-cli
forge init
forge scan
forge status
```

Or via pipx (if you don't use Homebrew):

```bash
pipx install forge-cli
```

## Why forge?

AI coding agents (Claude Code, Codex, Cursor) are powerful, but they start blind in every repo. forge gives them — and you — cross-project awareness:

- **See everything at once**: `forge status` shows all your repos with branch, dirty state, ahead/behind
- **Share context across projects**: `forge share "deploy: run migrations first" --group backend` — all agents in that group see it
- **Feature branches across repos**: `forge feature create "refactor-auth" --repos svc-a,svc-b` — creates git worktrees in one command
- **MCP for AI agents**: `forge serve` exposes 13 tools over stdio — any MCP-compatible agent calls them directly

## Quick Start

```bash
# Install (Homebrew — recommended for Forge OS)
brew tap modib/forge
brew install forge-cli

# Or via pipx (works anywhere)
# pipx install forge-cli

# Initialize
forge init --provider github

# Discover existing repos
forge scan

# See workspace status
forge status

# Check dev environment
forge health
```

## Commands

| Command | Description |
|---------|-------------|
| `forge init [--provider github]` | Initialize workspace config + auth |
| `forge scan` | Discover new git repos in ~/Workspace |
| `forge status [name] [--json]` | Show workspace/repo status |
| `forge health` | Check dev environment (brew, ollama, gh, disk) |
| `forge clone <url> [--name]` | Clone + register in workspace |
| `forge feature create <name> [--repos a,b]` | Create feature |
| `forge feature list` | List active features |
| `forge feature worktree <id> --repo <name>` | Create git worktree for feature |
| `forge share <content> [--group g]` | Share note across projects |
| `forge notes [group]` | List shared notes |
| `forge serve` | Start MCP stdio server |
| `forge config` | Show config path |

## MCP Server

Any MCP-compatible AI agent connects to forge via stdio:

```bash
# Terminal 1: Start MCP server
forge serve

# In your AI agent (Claude Code, Codex, etc.):
#   → forge serves 13 tools:
#     list_repos, repo_status, workspace_status, workspace_health,
#     clone_repo, workspace_scan, create_feature, list_features,
#     log_decision, get_decisions, start_session, share_note,
#     get_shared_notes
```

**Claude Code setup:**
```json
{
  "mcpServers": {
    "forge": {
      "command": "forge",
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
forge serve ───→ 13 MCP tools
  │
forge CLI ─────→ init, status, clone, feature, share
  │
  ▼
subprocess: git, brew, gh, graphify
```

forge is the workspace infrastructure layer. It does not compete with AI agents — it gives them workspace superpowers.

## State

```
~/.forge/              # (also checks ~/.workspace for backward compat)
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

# forge status provides machine-readable input for graphify
forge status --json | graphify extract --stdin  # (future)
```

## Contributing

```bash
git clone https://github.com/forge/forge-cli
cd forge-cli
pipx install -e .
```

See [ROADMAP.md](./ROADMAP.md) for the development plan.

## Links

- **Docs:** https://modib.github.io/forge-cli/
- **Repo:** https://github.com/modib/forge-cli
- **Forge Project:** https://github.com/modib/forge

## License

MIT
