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

Creates `~/.forge/config.json` (fallback: `~/.workspace`) with provider settings. With `--provider github`, checks `gh auth status` and auto-detects GitHub username.

---

### `forge scan`

Discover new git repositories in workspace root.

```bash
forge scan
```

Scans `~/Workspace` for directories containing `.git`, registers any new ones in config. Skips already-registered repos.

---

### `forge status`

Show workspace or repository status.

```bash
forge status [name] [--json]
```

Without `name`, shows all registered repos with:
- Branch name
- Dirty state (● = uncommitted changes)
- Ahead/behind counts
- Last commit message

With `name`, shows status for a specific repo.

With `--json`, outputs machine-readable JSON (includes all fields for all repos).

---

### `forge health`

Check dev environment health.

```bash
forge health
```

Checks for: `brew`, `ollama`, `gh`, `python3`, `node`, `npm`, `gh auth`, disk space usage.

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
```

**`create`**: Creates a new feature with optional repo list. Generates a unique feature ID (`feat-<hex>`).

**`list`**: Lists all active features and their worktree count.

**`worktree`**: Creates a git worktree for a repo in the feature. Without `--repo`, lists repos in the feature. Worktrees go in `~/.forge/.workspaces/<feature-id>/<repo>/` (fallback: `~/.workspace`).

---

### `forge share`

Share a note across projects in a group.

```bash
forge share <content> [--group <name>] [--label <label>]
```

Notes are stored in `~/.forge/config.json` (fallback: `~/.workspace`) under `groups[].notes`. Any agent or user in the group can read them.

---

### `forge notes`

List shared notes for a group.

```bash
forge notes [group]
```

Default group is `"default"`. Shows timestamp, label, and content for each note.

---

### `forge serve`

Start the MCP stdio server.

```bash
forge serve
```

Exposes 13 tools over stdio for MCP-compatible AI agents. See [MCP server docs](./mcp.md).

---

### `forge config`

Show config file path or validate workspace config.

```bash
forge config
forge config validate [--fix]
```

Prints the absolute path to `~/.forge/config.json` (fallback: `~/.workspace`). With `validate`, checks for issues like missing repos, stale worktrees, and duplicate entries; `--fix` removes stale worktrees.

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

Detects: CPU model/cores, RAM total/available, NVIDIA/AMD/Apple GPU, disk space, Apple Silicon, MLX availability. Recommends a backend (`ollama` for Intel/Linux, `mlx` for Apple Silicon) and a model size.

---

### `forge ai setup`

Install AI backend and pull a model.

```bash
forge ai setup                           # Auto-detect backend
forge ai setup --backend ollama          # Install Ollama + model
forge ai setup --backend mlx             # Install MLX + mlx-lm (Apple Silicon only)
forge ai setup --model qwen2.5-coder:7b  # Specify model
```

On Intel/Linux: installs Ollama, pulls a Gemma model (e.g. `gemma2:2b` for 8GB RAM, `gemma3:7b` for 16GB+). On Apple Silicon: installs `mlx` + `mlx-lm` via pip, suggests a Qwen2.5-Coder model from mlx-community.

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
forge ai config routing.local "phi-4-mini:3.8b"  # Set model for local routing
forge ai config provider                 # Unset/remove a key
```

Config is stored in `~/.forge/config.json` (fallback: `~/.workspace`) under the `ai` key.

---

### `forge ai benchmark`

Run an inference speed test.

```bash
forge ai benchmark                           # Default model + backend
forge ai benchmark --backend mlx             # Test MLX backend
forge ai benchmark --model qwen2.5-coder:7b --prompt "Write a function"
```

Reports: model, prompt snippet, response length, latency (ms), tokens/sec.

---

### `forge exec`

Execute a natural language workspace command. No flags needed — it just works.

```bash
forge exec "show me dirty repos"           # Keyword match → forge status
forge exec "scan for new repos"            # Keyword match → forge scan
forge exec "find vulnerable libraries"     # Keyword match → forge scan
```

**Resolution chain** (automatic, transparent):
1. **Keyword patterns** — instant match for common queries (no model needed)
2. **GitHub Models free tier** — if `gh` is authenticated, tries cloud API (fast, no setup)
3. **Local model** — Ollama with Gemma (`gemma2:2b`), auto-pulled on first use, shows progress:
   ```
    forge: downloading gemma2:2b (this may take a minute)...
    forge: model ready
   ```

Each step shows a brief note on stderr: `forge: resolved by GitHub Models` or `forge: resolved by local model (ollama)`. If no resolver succeeds, you'll get a helpful message with an example.

---

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)**
