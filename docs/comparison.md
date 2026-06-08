# Comparison

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)** · **[Comparison](./comparison.md)**

---

> **`gh` and GitHub MCP Server talk to GitHub's API. Forge talks to your local workspace — all repos, git state, dependencies, CVEs, agent sessions, and shared decisions — and runs offline on old 8GB laptops with zero cloud dependencies.**

Forge is not a replacement for GitHub CLI or GitHub MCP Server. It is a complementary layer that adds local workspace intelligence. The three tools work together:

- **GitHub CLI (`gh`)** — GitHub API client for single-repo operations
- **GitHub MCP Server** — MCP bridge to GitHub API for AI agents
- **Forge** — Local workspace infrastructure: cross-repo awareness, dependency parsing, CVE scanning, RAG, agent sessions

## Forge CLI vs GitHub CLI

| Capability | GitHub CLI (`gh`) | Forge CLI | Benefit |
|------------|-------------------|-----------|---------|
| **Multi-repo status** | Single repo at a time | `forge status` — all repos, branch, dirty, ahead/behind | See workspace health at a glance |
| **Dependency parsing** | None | 6 lockfile parsers (npm, Cargo, PyPI, Go, Ruby) | Know every package across all projects |
| **CVE scanning** | Dependabot alerts (GH repos only) | `forge cve refresh` — OSV.dev, any ecosystem, no PAT | Security scanning for any repo, even self-hosted |
| **CVE fix information** | None | `forge cve fix <id>` — shows safe version, affected lockfiles | Know exactly what to upgrade |
| **Semantic search / RAG** | None | `forge ask "what uses lodash?"` — nomic-embed-text + Gemma 4 | Ask questions about your workspace in natural language |
| **Offline operation** | Requires GitHub API | Status, deps, RAG all offline (CVE refresh needs network) | Works on a plane, air-gapped, or with spotty internet |
| **Feature branching** | Single-repo branches | `forge feature create "refactor" --repos a,b,c` — multi-repo worktrees | Coordinated branching across polyrepo projects |
| **Agent sessions** | None | `forge sessions search "auth"`, `forge sessions diff <a> <b>` | Audit trail and traceability for AI agents |
| **Agent handoff** | None | `forge agent handoff <sid> --to codex` — packages transcript + decisions | Pass context between Claude Code, Codex, etc. |
| **Cross-project notes** | None | `forge share "run migrations" --group backend` | Institutional memory visible to all agents |
| **NL command routing** | Structured CLI only | `forge exec "what's dirty?"` → keyword/LLM → forge command | Natural language as CLI interface |
| **Hardware-aware AI** | None | Detects RAM/CPU/GPU, picks Gemma 4 E2B (8GB) or E4B (16GB+) | Runs on old laptops without GPU |
| **LLM fallback chain** | N/A | Keyword → GitHub Models free tier → local Ollama Gemma 4 | Zero API cost for common queries |
| **Install** | `brew install gh` | `brew install modib/forge/forge-cli` or `pipx install forge-cli` | No Docker, no PAT required for local features |
| **Docker required?** | No (native binary) | No (pure Python) | Zero infrastructure overhead |

## Forge MCP Server vs GitHub MCP Server

| Capability | GitHub MCP Server | Forge MCP Server | Benefit |
|------------|-------------------|------------------|---------|
| **Domain** | GitHub.com API (remote repos) | Local `~/Workspace` (repos on disk) | Both at once — GH for remote, Forge for local |
| **Auth model** | GitHub PAT with scopes | None — reads local filesystem | No token management, no scope errors |
| **Workspace intelligence** | None — single-repo API calls | 26 tools: `workspace_status`, `workspace_health`, `workspace_doctor`, `workspace_scan` | AI agent knows about all local repos simultaneously |
| **Dependency/CVE awareness** | Dependabot alerts (GH repos only) | `cve_fix_info` tool — OSV.dev for any ecosystem | Fix CVEs in non-GH projects |
| **Agent sessions & handoff** | None | `start_session` + `agent_handoff` tools — transcripts, decisions, handoff documents | Pass context between agents |
| **Git worktree management** | None | `create_feature` + `log_decision` tools | Feature branches with shared decisions across repos |
| **Shared notes** | None | `share_note` + `get_shared_notes` tools | Cross-project decisions visible to all agents |
| **Graph analysis** | None | `generate_graph` — co-change relationships between files | Understand which files change together |
| **Local-first** | Requires Docker + GitHub PAT + internet | `forge serve` — stdio, zero auth, works offline | No infra, no secrets, no cloud |
| **Install size** | Go binary + Docker (~500MB+) | Python package (~200KB + stdlib) | Lightning startup, minimal footprint |
| **Hardware awareness** | None | `ai_detect` + `ai_setup` tools — probes RAM/GPU, recommends model | AI model selection tailored to the machine |
| **Container required** | Yes (Docker) | No | Run directly, no Docker daemon needed |
| **PR & Issue operations** | Full GitHub API (create/edit/list) | Delegates to `gh` under the hood (`forge pr create`) | Complementary — use both servers simultaneously |

## When to Use Which

```
┌───────────────────────────────────────────────────────┐
│                   AI Agent                              │
│    (Claude Code, Codex, Gemini CLI, Cursor, OpenCode)  │
└──────┬──────────────────────────┬─────────────────────┘
       │ MCP stdio                │ MCP stdio
       ▼                          ▼
┌────────────────────┐  ┌───────────────────────────┐
│ GitHub MCP Server  │  │ Forge MCP Server          │
│                    │  │                           │
│ Repos, Issues,     │  │ Workspace: status, health │
│ PRs, Actions,      │  │ Dependencies (6 ecosystems)│
│ Code Scanning,     │  │ CVE scanning (OSV.dev)    │
│ Dependabot,        │  │ Agent sessions + handoff  │
│ Discussions,       │  │ Feature worktrees + notes │
│ Users, Orgs, Gists │  │ RAG semantic search       │
│                    │  │ Knowledge graphs          │
│ Talks to:          │  │ NL exec routing           │
│  GitHub API        │  │                           │
└────────────────────┘  │ Talks to:                 │
                        │  Local filesystem + git   │
                        │  + Ollama + OSV.dev       │
                        └───────────────────────────┘
```

### Decision guide

| Use case | Tool |
|----------|------|
| Create a GitHub issue or PR | `gh` or GitHub MCP Server |
| List workflows, view Actions logs | `gh` or GitHub MCP Server |
| Browse remote file contents on GitHub | GitHub MCP Server (`get_file_contents`) |
| See git status across all local repos | **Forge** (`forge status`, `workspace_status`) |
| Find what packages a project uses | **Forge** (`forge deps list`) |
| Scan for security vulnerabilities | **Forge** (`forge cve refresh / list / report`) |
| Fix a vulnerable dependency | **Forge** (`forge cve fix <id>`) |
| Search workspace history with RAG | **Forge** (`forge ask "what uses lodash?"`) |
| Search past agent sessions | **Forge** (`forge sessions search <query>`) |
| Hand off context between agents | **Forge** (`forge agent handoff <sid> --to codex`) |
| Run an AI model locally | **Forge** (`forge ai setup`, Gemma 4 E2B on Ollama) |
| Execute natural language as commands | **Forge** (`forge exec "show dirty repos"`) |

**You can use all three simultaneously** — they don't conflict. A Claude Code session can use GitHub MCP Server for remote API operations and Forge MCP Server for local workspace intelligence in the same conversation.

---

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)** · **[Comparison](./comparison.md)**
