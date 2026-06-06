# CLI Reference

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)**

---

## Global Options

| Flag | Description |
|------|-------------|
| `--version` | Show version |
| `--help` | Show help |

## Commands

### `ws init`

Initialize workspace config and provider auth.

```bash
ws init [--provider github|gitlab]
```

Creates `~/.workspace/config.json` with provider settings. With `--provider github`, checks `gh auth status` and auto-detects GitHub username.

---

### `ws scan`

Discover new git repositories in workspace root.

```bash
ws scan
```

Scans `~/Workspace` for directories containing `.git`, registers any new ones in config. Skips already-registered repos.

---

### `ws status`

Show workspace or repository status.

```bash
ws status [name] [--json]
```

Without `name`, shows all registered repos with:
- Branch name
- Dirty state (● = uncommitted changes)
- Ahead/behind counts
- Last commit message

With `name`, shows status for a specific repo.

With `--json`, outputs machine-readable JSON (includes all fields for all repos).

---

### `ws health`

Check dev environment health.

```bash
ws health
```

Checks for: `brew`, `ollama`, `gh`, `python3`, `node`, `npm`, `gh auth`, disk space usage.

---

### `ws clone`

Clone a repository and register it in workspace.

```bash
ws clone <url> [--name <name>]
```

Clones into `~/Workspace/<name>`. Auto-detects name from URL if `--name` is omitted.

---

### `ws feature`

Manage feature branches across one or more repos.

```bash
ws feature create <name> [--repos <a,b,c>]
ws feature list
ws feature worktree <id> [--repo <name>]
```

**`create`**: Creates a new feature with optional repo list. Generates a unique feature ID (`feat-<hex>`).

**`list`**: Lists all active features and their worktree count.

**`worktree`**: Creates a git worktree for a repo in the feature. Without `--repo`, lists repos in the feature. Worktrees go in `~/.workspace/.workspaces/<feature-id>/<repo>/`.

---

### `ws share`

Share a note across projects in a group.

```bash
ws share <content> [--group <name>] [--label <label>]
```

Notes are stored in `~/.workspace/config.json` under `groups[].notes`. Any agent or user in the group can read them.

---

### `ws notes`

List shared notes for a group.

```bash
ws notes [group]
```

Default group is `"default"`. Shows timestamp, label, and content for each note.

---

### `ws serve`

Start the MCP stdio server.

```bash
ws serve
```

Exposes 13 tools over stdio for MCP-compatible AI agents. See [MCP server docs](./mcp.md).

---

### `ws config`

Show config file path or validate workspace config.

```bash
ws config
ws config validate [--fix]
```

Prints the absolute path to `~/.workspace/config.json`. With `validate`, checks for issues like missing repos, stale worktrees, and duplicate entries; `--fix` removes stale worktrees.

---

### `ws completion`

Generate shell completion script for bash, zsh, or fish.

```bash
ws completion bash   # → source this in your .bashrc
ws completion zsh    # → place in a compdef directory
ws completion fish   # → source this in config.fish
```

---

### `ws ai detect`

Probe hardware and suggest AI backend + model.

```bash
ws ai detect                     # Text output
ws ai detect --json              # Machine-readable JSON
ws ai detect --backend mlx       # Show suggestion for MLX backend
```

Detects: CPU model/cores, RAM total/available, NVIDIA/AMD/Apple GPU, disk space, Apple Silicon, MLX availability. Recommends a backend (`ollama` for Intel/Linux, `mlx` for Apple Silicon) and a model size.

---

### `ws ai setup`

Install AI backend and pull a model.

```bash
ws ai setup                           # Auto-detect backend
ws ai setup --backend ollama          # Install Ollama + model
ws ai setup --backend mlx             # Install MLX + mlx-lm (Apple Silicon only)
ws ai setup --model qwen2.5-coder:7b  # Specify model
```

On Intel/Linux: installs Ollama, pulls a GGUF model. On Apple Silicon: installs `mlx` + `mlx-lm` via pip, suggests a safetensors model.

---

### `ws ai status`

Check whether the AI model backend is ready for inference.

```bash
ws ai status                          # Auto-detect backend
ws ai status --backend ollama         # Check Ollama readiness
ws ai status --backend mlx            # Check MLX readiness (Apple Silicon only)
```

Returns: ✓ ready or ✗ not ready with guidance on next steps.

---

### `ws ai config`

View or modify AI routing configuration.

```bash
ws ai config                          # Show all AI config
ws ai config backend ollama           # Set backend
ws ai config routing.local "phi-4-mini:3.8b"  # Set model for local routing
ws ai config provider                 # Unset/remove a key
```

Config is stored in `~/.workspace/config.json` under the `ai` key.

---

### `ws ai benchmark`

Run an inference speed test.

```bash
ws ai benchmark                           # Default model + backend
ws ai benchmark --backend mlx             # Test MLX backend
ws ai benchmark --model qwen2.5-coder:7b --prompt "Write a function"
```

Reports: model, prompt snippet, response length, latency (ms), tokens/sec.

---

### `ws exec`

Execute a natural language workspace command. Uses keyword matching first, then falls back to the local AI model (Ollama/MLX) for unrecognized queries.

```bash
ws exec "show me dirty repos"                 # Keyword match → ws status
ws exec "scan for new repos" --dry-run        # Preview intent + resolution method
ws exec "what branches are ahead of main"     # Keyword fail → LLM fallback
ws exec "what branches are ahead" --use-llm   # Force LLM resolution
ws exec "find all dirty repos" --use-llm --backend ollama  # Specify backend
```

**Resolution priority:**
1. Hardcoded keyword patterns (fast, no model needed)
2. LLM fallback via Ollama or MLX (when keyword fails and model is available)
3. `--use-llm` flag forces LLM for all queries (bypasses keyword matching)

Understands: status, scan, health, doctor, feature list, log, and help intents. Maps them to the corresponding ws command and returns output.

---

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)**
