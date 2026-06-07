# forge Workspace Schema & MCP Tool Reference

## State Model (`~/.forge/config.json`)

```jsonc
{
  "version": 1,                          // Schema version
  "workspace_root": "~/Workspace",        // Root directory for all projects

  // Git provider authentication state
  "providers": {
    "github": {
      "username": "user",
      "host": "github.com"
    },
    "gitlab": {
      "username": "",
      "host": "gitlab.com"
    }
  },

  // Registered repositories
  "repos": [
    {
      "name": "my-project",               // Directory name
      "path": "/home/user/Workspace/my-project",
      "provider": "github",               // github | gitlab | other
      "url": "git@github.com:user/my-project.git",
      "default_branch": "main",
      "pinned_commit": "",                // Optional: pin to specific commit
      "added": "2026-06-05T10:00:00+00:00"
    }
  ],

  // Named groups for cross-project context sharing
  "groups": [
    {
      "name": "backend",
      "repos": ["my-project", "another-project"],
      "notes": [                          // Shared notes visible to all repos in group
        {
          "content": "Deploy: run migrations before release",
          "label": "deploy",
          "timestamp": "2026-06-05T12:00:00+00:00"
        }
      ]
    }
  ],

  // Active feature branches
  "features": [
    {
      "id": "feat-abc12345",
      "name": "Refactor auth flow",
      "created": "2026-06-05T12:00:00+00:00",
      "repos": ["my-project", "another-project"],
      "worktrees": {
        "my-project": "/home/user/Workspace/.workspaces/feat-abc12345/my-project"
      },
      "decisions": [                      // Cross-worktree agent decisions
        {
          "timestamp": "2026-06-05T12:30:00+00:00",
          "message": "Changed User.ID to uuid",
          "author": "agent-claude",
          "type": "breaking"             // info | breaking | review
        }
      ]
    }
  ],

  // Agent session history
  "sessions": [
    {
      "id": "sess-abcdef123456",
      "feature": "feat-abc12345",
      "agent": "claude-code",
      "started": "2026-06-05T12:00:00+00:00",
      "context": "Initial prompt text...",
      "worktrees": ["my-project"]
    }
  ],

  // AI routing configuration
  "ai": {
    "provider": "ollama",
    "routing": {
      "local": "gemma4:e2b",
      "cloud": "github-models"
    }
  }
}
```

### File Locations

| Path | Purpose |
|------|---------|
| `~/.forge/config.json` | Workspace state (repos, groups, features, sessions, AI config) |
| `~/.forge/deps.json` | Parsed dependency cache (6 ecosystems) |
| `~/.forge/cve.json` | OSV.dev vulnerability cache |
| `~/.forge/sessions/<id>/meta.json` | Session metadata |
| `~/.forge/sessions/<id>/transcript.md` | Session transcript |
| `~/.forge/worktrees/<feature-id>/<repo>/` | Git worktrees for active feature |
| `~/.Brewfile` | Homebrew package manifest (brew bundle --global) |

## CLI Commands

| Command | Description |
|---------|-------------|
| `forge init [--provider github]` | Initialize workspace config + auth |
| `forge scan` | Discover new git repos + parse dependencies |
| `forge status [name] [--json] [--graph]` | Show workspace/repo status |
| `forge health` | Check dev environment tools |
| `forge doctor [--json]` | Diagnose workspace issues |
| `forge clone <url> [--name]` | Clone repo into workspace |
| `forge feature create/list/worktree/done` | Manage feature branches |
| `forge graph <name> [--type] [--format]` | Knowledge graph for any repo |
| `forge pr create <feature-id> [--title] [--body] [--draft]` | Create PRs with cross-references |
| `forge share <content> [--group g] [--label l]` | Share note across projects |
| `forge notes [group]` | List shared notes |
| `forge install claude|codex` | Install and configure AI agents |
| `forge log [id] [--limit] [--json]` | View agent session history |
| `forge config [path\|validate\|remove-repo]` | Manage workspace configuration |
| `forge deps list [--name] [--ecosystem]` | List project dependencies |
| `forge cve refresh\|list\|describe\|report` | CVE vulnerability scanning |
| `forge ai detect\|setup\|status\|config\|benchmark` | AI integration commands |
| `forge exec <query> [--dry-run]` | Natural language workspace command |
| `forge serve` | Start MCP stdio server |
| `forge completion bash\|zsh\|fish` | Generate shell completion script |

## MCP Tool Schema (24 Tools)

The `forge serve` command starts an MCP server over stdio. Connect any MCP-compatible AI agent (Claude Code, Codex, Gemini CLI).

### Repository Tools

#### `list_repos`
List all registered workspace repositories.
- **Args:** None
- **Returns:** `[{name, path, provider}]`

#### `repo_status`
Get git status for a specific repository.
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
Check dev environment health.
- **Args:** None
- **Returns:** `{brew, ollama, gh, python3, node, npm, gh_auth, disk_*}`

#### `workspace_doctor`
Diagnose workspace issues (missing repos, stale worktrees, no remotes).
- **Args:** None
- **Returns:** `{total_issues, issues: [{severity, detail, repo?, feature?}]}`

#### `workspace_scan`
Scan workspace root for new git repositories.
- **Args:** None
- **Returns:** `{total, new: [name, ...]}`

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
- **Args:** `feature_id` (string, required), `message` (string, required), `type` (info|breaking|review), `author` (string, required)
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
- **Args:** `name` (string, required), `graph_type` (co-change|branches, optional), `depth` (integer, optional)
- **Returns:** Graph data as JSON (nodes, edges, branches, history)

### PR Tools

#### `create_prs`
Create PRs across all repos in a feature with cross-references.
- **Args:** `feature_id` (string, required), `title` (string, optional), `body` (string, optional), `draft` (boolean, optional)
- **Returns:** `{feature, id, prs: [{repo, status, url?}]}`

### Config Tools

#### `validate_config`
Validate workspace configuration and optionally fix issues.
- **Args:** `fix` (boolean, optional)
- **Returns:** `{valid, issues, _repaired?}`

### Completion Tools

#### `generate_completion`
Generate shell completion script for bash, zsh, or fish.
- **Args:** `shell` (bash|zsh|fish, required)
- **Returns:** Shell completion script text

### AI Tools

#### `ai_detect`
Detect hardware profile (CPU, RAM, GPU, disk, Apple Silicon, MLX).
- **Args:** None
- **Returns:** `{platform, arch, cpu, memory, gpu, disk, apple_silicon, mlx_available, recommended_backend}`

#### `ai_config`
View or modify AI configuration.
- **Args:** `key` (string, optional), `value` (string, optional)
- **Returns:** Current AI config as JSON

#### `exec_nl`
Execute a natural language workspace command (keyword → GitHub Models → local model).
- **Args:** `query` (string, required), `dry_run` (boolean, optional)
- **Returns:** `{intent, command, output, resolved_by}`

#### `ai_setup`
Set up AI backend (ollama or mlx) and pull model.
- **Args:** `backend` (ollama|mlx, optional), `model` (string, optional)
- **Returns:** `{backend, model, log, ollama_installed?, mlx_installed?}`

#### `ai_benchmark`
Run inference benchmark on AI backend.
- **Args:** `model` (string, optional), `prompt` (string, optional), `backend` (ollama|mlx, optional)
- **Returns:** `{backend, model, latency_ms, tokens_per_sec, response_length}`

#### `ai_status`
Check whether AI model backend is ready for inference.
- **Args:** `backend` (ollama|mlx, optional), `model` (string, optional)
- **Returns:** `{ready: bool, backend, model, note?, error?}`

## Integration: graphify

The forge CLI can launch graphify as a subprocess for codebase knowledge graphs:

```bash
forge graph my-project                         # co-change graph
forge graph my-project --type branches         # branch/commit graph
forge status --json                            # forge status as JSON
```