# MCP Server

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)** · **[Comparison](./comparison.md)**

---

The `forge serve` command starts an MCP (Model Context Protocol) server over stdio. Any MCP-compatible AI agent — Claude Code, Codex CLI, Gemini CLI, Cursor — can connect and call workspace tools.

Contrast with [GitHub MCP Server](https://github.com/github/github-mcp-server), which gives AI agents access to the GitHub API. Forge MCP Server gives AI agents access to the **local workspace** — repos on disk, git state, dependency trees, CVEs, agent sessions, and shared notes. They are complementary: use both in the same conversation.

## Quick Start

```bash
# Terminal 1: Start server
forge serve
```

### Claude Code Setup

Add to your project's `.mcp.json` or `claude_desktop_config.json`:

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

### Codex CLI Setup

Add to `.codex/hooks.json` or configure in `~/.codex/config.json`:

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

## Tool Reference (26 tools)

### Repository Tools

#### `list_repos`

List all registered workspace repositories.

- **Args:** None
- **Returns:** `[{name, path, provider}]`

#### `repo_status`

Get git status for a repository.

- **Args:** `name` (string, required)
- **Returns:** `{name, branch, dirty, ahead, behind, last_commit_msg}`

#### `clone_repo`

Clone a repository into the workspace.

- **Args:** `url` (string, required), `name` (string, optional)
- **Returns:** `{status, path, name}`

### Workspace Tools

#### `workspace_status`

Get overall workspace status across all repos.

- **Args:** None
- **Returns:** `{total_repos, dirty, ahead, behind, missing, active_features, repos: [...]}`

#### `workspace_health`

Check dev environment health (brew, ollama, gh, python, node, disk).

- **Args:** None
- **Returns:** `{brew, ollama, gh, python3, node, npm, gh_auth, disk_total_gb, disk_free_gb, disk_used_pct}`

#### `workspace_doctor`

Diagnose workspace issues (missing repos, stale worktrees, no remotes).

- **Args:** None
- **Returns:** `{total_issues, issues: [{severity, detail, repo?, feature?}]}`

#### `workspace_scan`

Scan workspace root for new git repositories.

- **Args:** None
- **Returns:** `{total, new: [name, ...]}`

#### `validate_config`

Validate workspace configuration and optionally repair issues.

- **Args:** `fix` (boolean, optional)
- **Returns:** `{valid, issues, _repaired?}`

### Feature Tools

#### `create_feature`

Create a named feature with optional repo list.

- **Args:** `name` (string, required), `repos` (string[], optional)
- **Returns:** `{id, name, created, repos, worktrees, decisions}`

#### `list_features`

List all active features.

- **Args:** None
- **Returns:** `[{id, name, worktrees, ...}]`

### Decision Tools

#### `log_decision`

Log a cross-worktree decision for a feature.

- **Args:** `feature_id` (string, required), `message` (string, required), `type` (enum: `info`|`breaking`|`review`, required), `author` (string, required)
- **Returns:** `{timestamp, message, type, author}`

#### `get_decisions`

Get all decisions logged for a feature.

- **Args:** `feature_id` (string, required)
- **Returns:** `[{timestamp, message, type, author, ...}]`

### Agent Tools

#### `start_session`

Record the start of an agent session.

- **Args:** `agent` (string, required), `feature_id` (string, optional), `context` (string, optional)
- **Returns:** `{session_id}`

Creates a session directory at `<active-dir>/sessions/<id>/` (run `forge config path` for the active directory) with `meta.json` and `transcript.md`.

#### `agent_handoff`

Hand off a session context to another agent.

- **Args:** `session_id` (string, required), `target` (enum: `claude`|`codex`, required)
- **Returns:** `{session_id, handoff_to, handoff_json, handoff_md, transcript_length, decisions_count}`

Packages the session transcript, decisions, feature info, and workspace status into a handoff document that the target agent can read.

### Security Tools

#### `cve_fix_info`

Get fix instructions for a CVE vulnerability.

- **Args:** `vuln_id` (string, required — e.g., `GHSA-xxxx` or `CVE-2024-xxxx`)
- **Returns:** `{vuln_id, summary, cvss_score, fix_versions: [{package, ecosystem, introduced, fixed}], affected_repos}`

Queries OSV.dev for the full vulnerability detail, parses safe versions from the affected ranges, and maps them to the repos and lockfiles in your workspace.

### Context Tools

#### `share_note`

Share a note across projects in a group.

- **Args:** `content` (string, required), `group` (string, required), `label` (string, optional)
- **Returns:** `{status, group}`

#### `get_shared_notes`

Get shared notes for a group.

- **Args:** `group` (string, required)
- **Returns:** `[{content, label, timestamp}]`

### Graph Tools

#### `generate_graph`

Generate a knowledge graph for a workspace repo (co-change or branches).

- **Args:** `name` (string, required), `graph_type` (enum: `co-change`|`branches`, optional), `depth` (integer, optional)
- **Returns:** Graph data as JSON (nodes, edges, branches, history)

### PR Tools

#### `create_prs`

Create PRs across all repos in a feature with cross-references.

- **Args:** `feature_id` (string, required), `title` (string, optional), `body` (string, optional), `draft` (boolean, optional)
- **Returns:** `{feature, id, prs: [{repo, status, url?}]}`

### Completion Tools

#### `generate_completion`

Generate shell completion script for bash, zsh, or fish.

- **Args:** `shell` (enum: `bash`|`zsh`|`fish`, required)
- **Returns:** Shell completion script text

### AI Tools

#### `ai_detect`

Detect hardware profile (CPU, RAM, GPU, disk, Apple Silicon, MLX).

- **Args:** None
- **Returns:** `{platform, arch, cpu, memory, gpu, disk, apple_silicon, mlx_available, recommended_backend}`

#### `ai_status`

Check whether AI model backend is ready for inference.

- **Args:** `backend` (`ollama`|`mlx`, optional), `model` (string, optional)
- **Returns:** `{ready: bool, backend, model, note?, error?}`

#### `ai_config`

View or modify AI configuration.

- **Args:** `key` (string, optional), `value` (string, optional)
- **Returns:** Current AI config as JSON

#### `ai_setup`

Set up AI backend and pull model.

- **Args:** `backend` (`ollama`|`mlx`, optional), `model` (string, optional)
- **Returns:** `{backend, model, log, ollama_installed?, mlx_installed?}`

#### `ai_benchmark`

Run inference benchmark.

- **Args:** `model` (string, optional), `prompt` (string, optional), `backend` (`ollama`|`mlx`, optional)
- **Returns:** `{backend, model, latency_ms, tokens_per_sec, response_length}`

#### `exec_nl`

Execute a natural language workspace command (keyword → GitHub Models → local model).

- **Args:** `query` (string, required), `dry_run` (boolean, optional)
- **Returns:** `{intent, command, output, resolved_by}`

## Forge MCP vs GitHub MCP Server

| | GitHub MCP Server | Forge MCP Server |
|---|---|---|
| **What it gives AI agents** | GitHub API access (issues, PRs, repos, Actions) | Local workspace intelligence (git state, deps, CVEs, sessions, notes) |
| **Auth** | GitHub PAT with scopes | None — local filesystem |
| **Infrastructure** | Docker required | Pure Python, no container |
| **Offline** | No | Yes |
| **Tools** | Issues, PRs, Actions, Dependabot, code scanning, discussions, repos, users, gists | Workspace status/health/doctor, deps, CVEs, features, sessions, handoff, notes, graphs |
| **Use together?** | — | Yes — both MCP servers can run in the same agent session |

## Testing the MCP Server

```bash
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"0.1.0","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}\n{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}\n{"jsonrpc":"2.0","id":3,"method":"tools/list","params":{}}\n' | forge serve
```

## Protocol

forge uses the [Model Context Protocol](https://modelcontextprotocol.io) over stdio. The server:

1. Receives `initialize` request
2. Responds with server capabilities (26 tools)
3. Handles `tools/list` and `tools/call` requests
4. Returns results as `TextContent` in JSON-RPC responses

---

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)** · **[Comparison](./comparison.md)**
