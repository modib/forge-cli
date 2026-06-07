# Architecture

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)**

---

## Overview

forge is organized as three layers:

```
┌─────────────────────────────────────────────┐
│                 CLI Layer                     │
│  argparse-based interface (forge init, status)  │
├─────────────────────────────────────────────┤
│               Engine Layer                    │
│  State management, git ops, health checks    │
├─────────────────────────────────────────────┤
│              Integration Layer                │
│  MCP server (forge serve), graphify, subprocess │
└─────────────────────────────────────────────┘
```

## Module Map

| Module | Responsibility |
|--------|---------------|
| `cli.py` | Argument parsing, command dispatch, terminal output |
| `config.py` | Load/save `~/.forge/config.json` (fallback: `~/.workspace`), repo lookup |
| `engine.py` | Workspace scanning, status aggregation, health checks |
| `git.py` | Git subprocess wrapper (discover, status, clone) |
| `server.py` | MCP protocol server (23 tools over stdio) |

## State Flow

```
forge init
  → config.py: default_config() → save to ~/.forge/config.json

forge scan
  → config.py: load_config()
  → git.py: discover_repos(~/Workspace) → list of {name, path, url}
  → config.py: repo_by_path() → deduplicate → add_repo()
  → config.py: save_config()

forge status
  → config.py: load_config()
  → git.py: for each repo, get_status() → {branch, dirty, ahead/behind}
  → engine.py: get_overall_status() → aggregate + format
  → cli.py: terminal output or JSON

forge serve
  → server.py: MCP Server("forge")
  → stdio_server() → await JSON-RPC messages
  → list_tools() → return 23 tool definitions
  → call_tool(name, args) → dispatch to engine/config/git
  → return TextContent
```

## MCP Integration

```
Agent                    forge serve
  │                        │
  │── initialize ─────────→│
  │←────── result ────────│
  │── tools/list ─────────→│
  │←── 23 tool defs ──────│
  │── tools/call ─────────→│
  │   workspace_status     │──→ engine.get_overall_status()
  │←────── result ────────│←── JSON response
```

## Dependencies

**Zero runtime dependencies** for core CLI (stdlib only: `json`, `argparse`, `subprocess`, `shutil`, `os`).

**MCP server** adds one dependency: `mcp>=1.0.0` (the official Python MCP SDK).

## File Locations

```
~/.forge/                # (also checks ~/.workspace for backward compat)
├── config.json          # All workspace state (repos, groups, features, sessions)
├── sessions/<id>/       # Agent session artifacts
│   ├── meta.json        # Session metadata
│   └── transcript.md    # Full transcript (Markdown)
├── .workspaces/         # Feature worktrees
│   └── <feature-id>/
│       └── <repo>/      # git worktree
└── project-card.json    # Cached forge status --json output
```

---

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)**
```
