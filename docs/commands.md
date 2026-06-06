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

Show config file path.

```bash
ws config
```

Prints the absolute path to `~/.workspace/config.json`.

---

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)**
