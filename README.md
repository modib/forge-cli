# forge — Cross-Project Workspace CLI

**forge** is the command center for `~/Workspace`. It indexes git repos, tracks dependencies and CVEs, manages feature worktrees, shares context between projects, and exposes all operations as MCP tools for AI agents.

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
- **Know your dependencies**: `forge deps list` parses 6 lockfile formats across all repos; `forge cve list` shows known vulnerabilities
- **Scan for CVEs**: `forge cve refresh` queries OSV.dev; `forge cve report` summarizes risk across your workspace
- **Share context across projects**: `forge share "deploy: run migrations first" --group backend` — all agents in that group see it
- **Feature branches across repos**: `forge feature create "refactor-auth" --repos svc-a,svc-b` — creates git worktrees in one command
- **MCP for AI agents**: `forge serve` exposes 24 tools over stdio — any MCP-compatible agent calls them directly

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
| `forge scan` | Discover new git repos + parse deps |
| `forge status [name] [--json] [--graph]` | Show workspace/repo status |
| `forge health` | Check dev environment (brew, ollama, gh, disk) |
| `forge doctor` | Diagnose workspace issues |
| `forge clone <url> [--name]` | Clone + register in workspace |
| `forge feature create/list/worktree/done` | Manage feature branches |
| `forge graph <name> [--type]` | Knowledge graph for any repo |
| `forge pr create <feature>` | Create PRs with cross-references |
| `forge share <content> [--group g]` | Share note across projects |
| `forge notes [group]` | List shared notes |
| `forge config [path\|validate\|remove-repo]` | Manage workspace configuration |
| `forge deps list [--name] [--ecosystem]` | List project dependencies |
| `forge cve refresh\|list\|describe\|report` | CVE vulnerability scanning |
| `forge ai detect\|setup\|status\|config\|benchmark` | AI integration commands |
| `forge exec <query>` | Natural language workspace command |
| `forge install claude\|codex` | Install and configure AI agents |
| `forge serve` | Start MCP stdio server (24 tools) |
| `forge completion bash\|zsh\|fish` | Generate shell completion script |

## MCP Server

Any MCP-compatible AI agent connects to forge via stdio:

```bash
# Terminal 1: Start MCP server
forge serve

# In your AI agent (Claude Code, Codex, etc.):
#   → forge serves 24 tools:
#     list_repos, repo_status, workspace_status, workspace_health,
#     workspace_doctor, clone_repo, workspace_scan, create_feature,
#     list_features, log_decision, get_decisions, start_session,
#     share_note, get_shared_notes, generate_graph, create_prs,
#     validate_config, generate_completion, ai_detect, ai_config,
#     ai_setup, ai_status, ai_benchmark, exec_nl
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
forge serve ───→ 24 MCP tools
  │
forge CLI ─────→ init, status, clone, feature, share, deps, cve, ai, exec
  │
  ▼
subprocess: git, brew, gh, ollama
```

forge is the workspace infrastructure layer. It does not compete with AI agents — it gives them workspace superpowers.

## State

```
~/.forge/              # (also checks ~/.workspace for backward compat)
├── config.json       # Repos, groups, features, sessions, AI config
├── deps.json         # Parsed dependency cache (6 ecosystems)
├── cve.json          # OSV.dev vulnerability cache
├── sessions/<id>/    # Agent session artifacts
│   ├── meta.json
│   └── transcript.md
└── .workspaces/      # Git worktrees for features
```

All state is plain JSON. No server, no daemon, no lock-in.

## Integration: graphify

```bash
# Build a knowledge graph for any repo
forge graph my-project
forge graph my-project --type branches
```

## Contributing

```bash
git clone https://github.com/modib/forge-cli
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