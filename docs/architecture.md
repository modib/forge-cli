# Architecture

## Overview

ws is organized as three layers:

```
┌─────────────────────────────────────────────┐
│                 CLI Layer                     │
│  argparse-based interface (ws init, status)  │
├─────────────────────────────────────────────┤
│               Engine Layer                    │
│  State management, git ops, health checks    │
├─────────────────────────────────────────────┤
│              Integration Layer                │
│  MCP server (ws serve), graphify, subprocess │
└─────────────────────────────────────────────┘
```

## Module Map

| Module | Responsibility |
|--------|---------------|
| `cli.py` | Argument parsing, command dispatch, terminal output |
| `config.py` | Load/save `~/.workspace/config.json`, repo lookup |
| `engine.py` | Workspace scanning, status aggregation, health checks |
| `git.py` | Git subprocess wrapper (discover, status, clone) |
| `server.py` | MCP protocol server (13 tools over stdio) |

## State Flow

```
ws init
  → config.py: default_config() → save to ~/.workspace/config.json

ws scan
  → config.py: load_config()
  → git.py: discover_repos(~/Workspace) → list of {name, path, url}
  → config.py: repo_by_path() → deduplicate → add_repo()
  → config.py: save_config()

ws status
  → config.py: load_config()
  → git.py: for each repo, get_status() → {branch, dirty, ahead/behind}
  → engine.py: get_overall_status() → aggregate + format
  → cli.py: terminal output or JSON

ws serve
  → server.py: MCP Server("ws")
  → stdio_server() → await JSON-RPC messages
  → list_tools() → return 13 tool definitions
  → call_tool(name, args) → dispatch to engine/config/git
  → return TextContent
```

## MCP Integration

```
Agent                    ws serve
  │                        │
  │── initialize ─────────→│
  │←────── result ────────│
  │── tools/list ─────────→│
  │←── 13 tool defs ──────│
  │── tools/call ─────────→│
  │   workspace_status     │──→ engine.get_overall_status()
  │←────── result ────────│←── JSON response
```

## Dependencies

**Zero runtime dependencies** for core CLI (stdlib only: `json`, `argparse`, `subprocess`, `shutil`, `os`).

**MCP server** adds one dependency: `mcp>=1.0.0` (the official Python MCP SDK).

## File Locations

```
~/.workspace/
├── config.json          # All workspace state (repos, groups, features, sessions)
├── sessions/<id>/       # Agent session artifacts
│   ├── meta.json        # Session metadata
│   └── transcript.md    # Full transcript (Markdown)
├── .workspaces/         # Feature worktrees
│   └── <feature-id>/
│       └── <repo>/      # git worktree
└── project-card.json    # Cached ws status --json output
```
