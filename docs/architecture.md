# Architecture

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)** · **[Comparison](./comparison.md)**

---

## Overview

forge is organized as four layers:

```
┌─────────────────────────────────────────────┐
│                 CLI Layer                     │
│  argparse-based interface (23 subcommands)   │
├─────────────────────────────────────────────┤
│               Engine Layer                    │
│  State management, git ops, health checks     │
├─────────────────────────────────────────────┤
│            Intelligence Layer                 │
│  Deps (6 lockfiles), CVE (OSV.dev),          │
│  RAG (embeddings), agent sessions            │
├─────────────────────────────────────────────┤
│              Integration Layer                │
│  MCP server (forge serve, 26 tools),         │
│  graphify, subprocess (git, brew, gh, ollama)│
└─────────────────────────────────────────────┘
```

## Position in the AI Agent Ecosystem

Forge fills the gap that GitHub CLI and GitHub MCP Server leave empty — local workspace intelligence:

```
AI Agent (Claude Code / Codex / Gemini CLI / Cursor)
    │
    ├── MCP ─→ GitHub MCP Server ───→ GitHub API (remote repos, issues, PRs, Actions)
    │
    └── MCP ─→ Forge MCP Server ─────→ Local ~/Workspace (git state, deps, CVEs,
                                        RAG index, sessions, handoff, notes)
```

## Module Map

| Module | Responsibility |
|--------|---------------|
| `cli.py` | Argument parsing, command dispatch, terminal output |
| `config.py` | Load/save active config (`~/.forge/` primary, `~/.workspace/` fallback), repo lookup |
| `engine.py` | Workspace scanning, status aggregation, health checks, diagnostics, PR creation, agent handoff |
| `git.py` | Git subprocess wrapper (discover, status, clone) |
| `server.py` | MCP protocol server (26 tools over stdio) |
| `graph.py` | Knowledge graph generation (co-change analysis, branch visualization) |
| `ai.py` | Hardware detection, AI setup (Ollama/MLX), model suggestion, NL routing (22 intents) |
| `deps.py` | Dependency parsing (6 lockfile formats), caching in `deps.json` |
| `cve.py` | OSV.dev API client, CVE query + caching in `cve.json`, report, fix version extraction |
| `rag.py` | RAG engine — nomic-embed-text embeddings, pure Python cosine similarity, `forge ask` |
| `install.py` | AI agent install (Claude Code, Codex) with MCP config |

## State Flow

```
forge init
  → config.py: default_config() → save to active config

forge scan
  → config.py: load_config()
  → git.py: discover_repos(~/Workspace) → list of {name, path, url}
  → config.py: repo_by_path() → deduplicate → add_repo()
  → config.py: save_config()
  → deps.py: parse_repo_deps() for each repo → cache in deps.json
  → (if new repos) rag.py: build_index() → cache in index.json

forge status
  → config.py: load_config()
  → git.py: for each repo, get_status() → {branch, dirty, ahead/behind}
  → engine.py: get_overall_status() → aggregate + format

forge cve refresh
  → deps.py: list_deps() → all deps across all repos
  → cve.py: _query_osv() for each uncached dep
  → cve.py: _save_cache() → cve.json

forge cve fix <id>
  → cve.py: _fetch_vuln_detail() → OSV.dev API with affected ranges
  → cve.py: _parse_fix_versions() → extract safe versions
  → cve.py: _vulns_for_dep() → map to affected repos + lockfiles

forge ask <query>
  → rag.py: _ensure_embedding_model() → pull nomic-embed-text if missing
  → rag.py: _ollama_embed(query) → 768-dim vector
  → rag.py: search() → cosine similarity against index.json
  → rag.py: _ollama_generate() → Gemma 4 E2B answers with context

forge agent handoff <id> --to <agent>
  → engine.py: get_session(id) → read meta.json + transcript.md
  → engine.py: gather decisions, feature, workspace status
  → engine.py: write handoff JSON + markdown to <active-dir>/handoffs/

forge sessions search <query>
  → engine.py: iterate all sessions → match against id, agent, context, feature, transcript
  → return results with match field + excerpt

forge sessions diff <id-a> <id-b>
  → engine.py: get_session() for both IDs
  → difflib.unified_diff() on transcripts
  → return structured diff with metadata

forge serve
  → server.py: MCP Server("forge")
  → stdio_server() → await JSON-RPC messages
  → list_tools() → return 26 tool definitions
  → call_tool(name, args) → dispatch to engine/config/git/ai/rag/cve/deps
  → return TextContent
```

## MCP Integration

```
Agent                    forge serve
  │                        │
  │── initialize ─────────→│
  │←────── result ────────│
  │── tools/list ─────────→│
  │←── 26 tool defs ──────│
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
| `~/.forge/index.json` | RAG embedding index | Primary |
| `~/.workspace/index.json` | Same | Fallback |
| `~/.forge/sessions/<id>/` | Agent session artifacts | Primary |
| `~/.workspace/sessions/<id>/` | Same | Fallback |
| `~/.forge/handoffs/` | Agent handoff documents | Primary |
| `~/.workspace/handoffs/` | Same | Fallback |
| `~/.forge/.workspaces/` | Feature git worktrees | Primary |
| `~/.workspace/.workspaces/` | Same | Fallback |
| `~/.workspace/project-card.json` | Cached forge status --json output | Always under `~/.workspace/` |

---

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)** · **[Comparison](./comparison.md)**
