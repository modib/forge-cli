# CLI Reference

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)**

---

## Global Options

| Flag | Description |
|------|-------------|
| `--version` | Show version |
| `--help` | Show help |

## Commands

### `forge init`

Initialize workspace config and provider auth.

```bash
forge init [--provider github|gitlab]
```

Creates workspace config in the active directory. Run `forge config path` to see which location is used:

- `~/.forge/config.json` — primary location (created by `forge init`)
- `~/.workspace/config.json` — automatic fallback if `~/.forge/` doesn't exist

With `--provider github`, checks `gh auth status` and auto-detects GitHub username.

---

### `forge scan`

Discover new git repositories and parse dependencies in workspace root.

```bash
forge scan
```

Scans `~/Workspace` for directories containing `.git`, registers any new ones in config. Skips already-registered repos. Also parses dependencies from 6 lockfile formats for every registered repo.

---

### `forge status`

Show workspace or repository status.

```bash
forge status [name] [--json] [--graph]
```

Without `name`, shows all registered repos with:
- Branch name
- Dirty state (● = uncommitted changes)
- Ahead/behind counts
- Last commit message
- Remote status

With `name`, shows status for a specific repo.

With `--json`, outputs machine-readable JSON (includes all fields for all repos).

With `--graph`, shows cross-repo co-change impact for dirty repos.

---

### `forge health`

Check dev environment health.

```bash
forge health
```

Checks for: `brew`, `ollama`, `gh`, `python3`, `node`, `npm`, `gh auth`, disk space usage.

---

### `forge doctor`

Diagnose workspace issues.

```bash
forge doctor
forge doctor --json
```

Detects: missing repos (path not found), stale worktrees, repos without remotes, low disk space. JSON mode outputs machine-readable results.

---

### `forge clone`

Clone a repository and register it in workspace.

```bash
forge clone <url> [--name <name>]
```

Clones into `~/Workspace/<name>`. Auto-detects name from URL if `--name` is omitted.

---

### `forge feature`

Manage feature branches across one or more repos.

```bash
forge feature create <name> [--repos <a,b,c>]
forge feature list
forge feature worktree <id> [--repo <name>]
forge feature done <id>
```

**`create`**: Creates a new feature with optional repo list. Generates a unique feature ID (`feat-<hex>`).

**`list`**: Lists all active features and their worktree count.

**`worktree`**: Creates a git worktree for a repo in the feature. Without `--repo`, lists repos in the feature. Worktrees go in `<active-dir>/.workspaces/<feature-id>/<repo>/` (see `forge config path`).

**`done`**: Cleans up all worktrees and branches for a feature, removes from config.

---

### `forge graph`

Generate a knowledge graph for a workspace repo.

```bash
forge graph <name> [--type co-change|branches] [--depth <n>] [--format json|text]
```

**`co-change`**: Shows files that are frequently changed together (co-change relationships). Tracked across the last N commits (default: 50).

**`branches`**: Shows all branches and recent commit history.

---

### `forge pr`

Create pull requests across all repos in a feature with cross-references.

```bash
forge pr create <feature-id> [--title <title>] [--body <body>] [--draft]
```

Creates PRs in all repos belonging to the feature. Each PR body includes cross-references to sibling PRs.

---

### `forge share`

Share a note across projects in a group.

```bash
forge share <content> [--group <name>] [--label <label>]
```

Notes are stored in `<active-dir>/config.json` under `groups[].notes` (run `forge config path` to find the active directory). Any agent or user in the group can read them.

---

### `forge notes`

List shared notes for a group.

```bash
forge notes [group]
```

Default group is `"default"`. Shows timestamp, label, and content for each note.

---

### `forge install`

Install and configure AI agents (Claude Code, Codex).

```bash
forge install claude
forge install codex
```

Auto-detects the agent binary, configures MCP server settings, and sets up environment variables.

---

### `forge log`

View agent session history.

```bash
forge log               # List recent sessions
forge log <session-id>  # View session details + transcript
forge log --json        # Machine-readable output
forge log --limit <n>   # Max sessions to list
```

---

### `forge serve`

Start the MCP stdio server.

```bash
forge serve
```

Exposes 24 tools over stdio for MCP-compatible AI agents. See [MCP server docs](./mcp.md).

---

### `forge config`

Manage workspace configuration. Config lives in `~/.forge/config.json` (or `~/.workspace/config.json` as fallback — run `forge config path` to see the active path).

```bash
forge config                     # Show config file path
forge config validate            # Validate workspace config
forge config validate --fix      # Auto-repair issues
forge config remove-repo <name>  # Remove a repo from config
```

With `validate`, checks for issues like missing repos, stale worktrees, and duplicate entries. `--fix` removes stale worktrees and repos with missing paths.

`remove-repo` removes a repo entry from config by name (no filesystem changes).

---

### `forge deps`

Manage project dependencies.

```bash
forge deps list                      # List all deps across all repos
forge deps list --name <repo>        # List deps for a specific repo
forge deps list --ecosystem pypi     # Filter by ecosystem
forge deps outdated                  # Points to: forge cve list
```

Parses 6 lockfile formats: `package-lock.json` (npm), `Cargo.lock` (Rust), `pyproject.toml` + `requirements.txt` (Python), `go.sum` (Go), `Gemfile.lock` (Ruby). Cached in `<active-dir>/deps.json` (run `forge config path` for the active directory).

---

### `forge cve`

CVE vulnerability scanning via OSV.dev API.

```bash
forge cve refresh                        # Query OSV.dev for all deps
forge cve list                           # List cached CVEs
forge cve list --ecosystem npm           # Filter by ecosystem
forge cve list --min-score 7.0           # Only high+ severity
forge cve describe CVE-2024-1234         # Show vulnerability details
forge cve describe CVE-2024-1234 --refresh  # Re-fetch from OSV.dev
forge cve report                         # Aggregate security summary
forge cve report --min-score 7.0         # High+ severity only
```

Results cached in `<active-dir>/cve.json` (run `forge config path` for the active directory). The `report` command breaks down by severity (critical/high/moderate/low/unknown), ecosystem, and top affected packages.

---

### `forge completion`

Generate shell completion script for bash, zsh, or fish.

```bash
forge completion bash   # → source this in your .bashrc
forge completion zsh    # → place in a compdef directory
forge completion fish   # → source this in config.fish
```

---

### `forge ai detect`

Probe hardware and suggest AI backend + model.

```bash
forge ai detect                     # Text output
forge ai detect --json              # Machine-readable JSON
forge ai detect --backend mlx       # Show suggestion for MLX backend
```

Detects: CPU model/cores, RAM total/available, NVIDIA/AMD/Apple GPU, disk space, Apple Silicon, MLX availability. Recommends a backend (`ollama` for Intel/Linux, `mlx` for Apple Silicon) and model.

---

### `forge ai setup`

Install AI backend and pull a model.

```bash
forge ai setup                           # Auto-detect backend
forge ai setup --backend ollama          # Install Ollama + model
forge ai setup --backend mlx             # Install MLX + mlx-lm (Apple Silicon only)
forge ai setup --model gemma4:e2b        # Specify model
```

On Intel/Linux: installs Ollama, pulls a Gemma 4 model (`gemma4:e2b` for 8GB RAM, `gemma4:e4b` for 16GB+). On Apple Silicon: installs `mlx` + `mlx-lm` via pip, suggests a Qwen2.5-Coder model from mlx-community. Shows download progress during model pull.

---

### `forge ai status`

Check whether the AI model backend is ready for inference.

```bash
forge ai status                          # Auto-detect backend
forge ai status --backend ollama         # Check Ollama readiness
forge ai status --backend mlx            # Check MLX readiness (Apple Silicon only)
```

Returns: ✓ ready or ✗ not ready with guidance on next steps.

---

### `forge ai config`

View or modify AI routing configuration.

```bash
forge ai config                          # Show all AI config
forge ai config backend ollama           # Set backend
forge ai config routing.local "gemma4:e2b"  # Set model for local routing
forge ai config provider                 # Unset/remove a key
```

Config is stored in `<active-dir>/config.json` under the `ai` key (run `forge config path` for the active directory).

---

### `forge ai benchmark`

Run an inference speed test.

```bash
forge ai benchmark                           # Default model + backend
forge ai benchmark --backend mlx             # Test MLX backend
forge ai benchmark --model gemma4:e2b --prompt "Write a function"
```

Reports: model, prompt snippet, response length, latency (ms), tokens/sec.

---

### `forge exec`

Execute a natural language workspace command. No flags needed — it just works.

```bash
forge exec "show dirty repos"              # Keyword match → forge status
forge exec "scan for new repos"            # Keyword match → forge scan
forge exec "find vulnerable libraries"     # Keyword match → forge cve refresh + list
forge exec "list dependencies"             # Keyword match → forge deps list
forge exec "create feature refactor-auth"  # → forge feature create (or falls through to LLM)
forge exec --dry-run "show status"         # Preview intent without executing
```

**Keyword intents** (instant, no model needed):

| Intent | Runs | Triggers |
|--------|------|----------|
| `status` | `forge status` | dirty, behind, ahead, workspace state |
| `scan` | `forge scan` | discover repos, find new repos |
| `init` | `forge init` | init, initialize, first time setup |
| `clone` | `forge clone` | clone repo, checkout project |
| `health` | `forge health` | environment, dev environment |
| `doctor` | `forge doctor` | diagnose, workspace issues |
| `cve_refresh` | `cve refresh && cve list` | vulnerable, security, cve |
| `cve_report` | `forge cve report` | security report, risk report |
| `cve_describe` | `forge cve describe` | cve details, describe cve |
| `deps_list` | `forge deps list` | dependencies, list deps, what packages |
| `feature_list` | `forge feature list` | list features, active features |
| `feature_create` | `forge feature create` | create feature, new feature |
| `graph` | `forge graph` | knowledge graph, co-change |
| `pr` | `forge pr create` | create pr, pull request |
| `share` | `forge share` | share note, save decision |
| `notes` | `forge notes` | my notes, list notes, shared notes |
| `install` | `forge install` | install agent, setup claude |
| `config_validate` | `forge config validate --fix` | validate config, fix config |
| `log` | `forge log` | sessions, history, recent |
| `ai_setup` | `forge ai setup` | setup ai, install model, configure ollama |
| `ai_status` | `forge ai status` | ai ready, check ollama, model status |
| `help` | `forge --help` | help, commands, what can you do |

Longer, more specific patterns take priority over shorter ones (e.g., "security issues" → `cve_refresh`, not `doctor`).

**Resolution chain** (automatic, transparent):
1. **Keyword patterns** — instant match for 22 intents (no model needed)
2. **GitHub Models free tier** — if `gh` is authenticated, tries cloud API (fast, no setup)
3. **Local model** — Ollama with Gemma 4 (`gemma4:e2b`), auto-pulled on first use

Each step shows a brief note on stderr: `forge: resolved by GitHub Models` or `forge: resolved by local model (ollama)`. If no resolver succeeds, you'll get a helpful message with an example.

---

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)**