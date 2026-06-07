# Architecture

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)**

---

## Overview

forge is organized as three layers:

```
┌─────────────────────────────────────────────┐
│                 CLI Layer                     │
│  argparse-based interface (forge init, status)│
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
| `config.py` | Load/save active config (see `forge config path`), repo lookup |
| `engine.py` | Workspace scanning, status aggregation, health checks, diagnostics, PR creation |
| `git.py` | Git subprocess wrapper (discover, status, clone) |
| `server.py` | MCP protocol server (24 tools over stdio) |
| `graph.py` | Knowledge graph generation (co-change analysis, branch visualization) |
| `ai.py` | Hardware detection, AI setup (Ollama/MLX), model suggestion, NL routing |
| `deps.py` | Dependency parsing (6 lockfile formats), caching in `deps.json` |
| `cve.py` | OSV.dev API client, CVE query + caching in `cve.json`, report generation |
| `install.py` | AI agent install (Claude Code, Codex) with MCP config |

## State Flow

```
forge init
  → config.py: default_config() → save to active config (see forge config path)

forge scan
  → config.py: load_config()
  → git.py: discover_repos(~/Workspace) → list of {name, path, url}
  → config.py: repo_by_path() → deduplicate → add_repo()
  → config.py: save_config()
  → deps.py: parse_repo_deps() for each repo → cache in active-dir/deps.json

forge status
  → config.py: load_config()
  → git.py: for each repo, get_status() → {branch, dirty, ahead/behind}
  → engine.py: get_overall_status() → aggregate + format
  → cli.py: terminal output or JSON

forge cve refresh
  → deps.py: list_deps() → all deps across all repos
  → cve.py: _query_osv() for each uncached dep
  → cve.py: _save_cache() → active-dir/cve.json

forge serve
  → server.py: MCP Server("forge")
  → stdio_server() → await JSON-RPC messages
  → list_tools() → return 24 tool definitions
  → call_tool(name, args) → dispatch to engine/config/git/ai
  → return TextContent
```

## MCP Integration

```
Agent                    forge serve
  │                        │
  │── initialize ─────────→│
  │←────── result ────────│
  │── tools/list ─────────→│
  │←── 24 tool defs ──────│
  │── tools/call ─────────→│
  │   workspace_status     │──→ engine.get_overall_status()
  │←────── result ────────│←── JSON response
```

## Dependencies

**Zero runtime dependencies** for core CLI (stdlib only: `json`, `argparse`, `subprocess`, `shutil`, `os`).

**MCP server** adds one dependency: `mcp>=1.0.0` (the official Python MCP SDK).

## File Locations

The active workspace directory depends on which exists at runtime. `forge config path` shows the actual path.

| Path | Purpose | When used |
|------|---------|-----------|
| `~/.forge/config.json` | Workspace state (repos, groups, features, sessions, AI config) | Primary — when `~/.forge/` exists |
| `~/.workspace/config.json` | Same schema | Fallback — used if `~/.forge/` doesn't exist |
| `~/.forge/deps.json` | Parsed dependency cache | Primary |
| `~/.workspace/deps.json` | Same | Fallback |
| `~/.forge/cve.json` | OSV.dev vulnerability cache | Primary |
| `~/.workspace/cve.json` | Same | Fallback |
| `~/.forge/sessions/<id>/` | Agent session artifacts | Primary |
| `~/.workspace/sessions/<id>/` | Same | Fallback |
| `~/.forge/.workspaces/` | Feature git worktrees | Primary |
| `~/.workspace/.workspaces/` | Same | Fallback |
| `~/.workspace/project-card.json` | Cached forge status --json output | Always under `~/.workspace/` |

---

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)**