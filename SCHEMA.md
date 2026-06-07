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
  ]
}
```

### File Locations

| Path | Purpose |
|------|---------|
| `~/.forge/config.json` | Workspace state (repos, groups, features, sessions) |
| `~/.forge/sessions/<id>/meta.json` | Session metadata |
| `~/.forge/sessions/<id>/transcript.md` | Session transcript |
| `~/.forge/worktrees/<feature-id>/<repo>/` | Git worktrees for active feature |
| `~/.Brewfile` | Homebrew package manifest (brew bundle --global) |

## CLI Commands

| Command | Description |
|---------|-------------|
| `forge init [--provider github]` | Initialize workspace config + auth |
| `forge scan` | Discover new git repos in workspace root |
| `forge status [name] [--json]` | Show workspace/repo status |
| `forge clone <url> [--name]` | Clone repo into workspace |
| `forge health` | Check dev environment tools |
| `forge feature create <name> [--repos a,b]` | Create feature |
| `forge feature list` | List features |
| `forge feature worktree <id> [--repo name]` | Manage worktrees |
| `forge share <content> [--group g] [--label l]` | Share note across projects |
| `forge notes [group]` | List shared notes |
| `forge serve` | Start MCP stdio server |
| `forge config` | Show config file path |

## MCP Tool Schema (13 Tools)

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

## Integration: graphify

The forge CLI can launch graphify as a subprocess for codebase knowledge graphs:

```bash
graphify clone https://github.com/user/repo     # graphify's own clone
forge status --json                              # forge status as JSON
graphify query "how does auth work?"             # query graph
```

Long-term: `forge status --json | graphify extract --stdin` for workspace-wide codebase understanding.
