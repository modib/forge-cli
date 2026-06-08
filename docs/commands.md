# Commands Reference

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)** · **[Comparison](./comparison.md)**

---

## Commands (23 subcommands)

| Command | Action | Description |
|---------|--------|-------------|
| `forge init` | init | Initialize workspace configuration |
| `forge config` | config | View config path or validate/repair config |
| `forge scan` | scan | Discover git repos in workspace root |
| `forge status` | status | Show workspace status across all repos |
| `forge health` | health | Check dev environment health |
| `forge doctor` | doctor | Diagnose workspace issues |
| `forge deps` | deps | List parsed dependencies grouped by repo |
| `forge cve` | cve | Refresh CVE cache, list CVEs, show CVE report, or get CVE fix info |
| `forge ask` | ask | Ask a natural language question about your workspace |
| `forge exec` | exec | Execute natural language as a forge command |
| `forge feature` | feature | Create or list features |
| `forge decision` | decision | Log or get feature decisions |
| `forge pr` | pr | Create PRs for a feature |
| `forge share` | share | Share a note across projects |
| `forge graph` | graph | Generate a knowledge graph |
| `forge index` | index | Build or check the RAG index |
| `forge ai` | ai | Detect, status, config, setup, benchmark AI |
| `forge agent` | agent | Hand off session context to another agent |
| `forge sessions` | sessions | Search, diff, or list agent sessions |
| `forge serve` | serve | Start MCP server over stdio |
| `forge completion` | completion | Generate shell completion script |
| `forge log` | log | Show workspace event log |
| `forge watch` | watch | Watch workspace for changes |

## Agent Session Commands (v0.5.0)

### `forge agent handoff <session-id> --to <agent>`

Package a session transcript + decisions + feature context into a handoff document for another agent.

- `<session-id>`: The session ID to hand off (required)
- `--to`: Target agent — `claude`, `codex` (required)
- Output: JSON + markdown handoff documents in `<active-dir>/handoffs/`

### `forge sessions search <query>`

Full-text search across all agent session metadata and transcripts.

- `<query>`: Search string (matched against session IDs, agent names, context, features, and transcripts)
- `--limit N`: Maximum results (default: 10)
- Returns: Matched session info with excerpt from transcript

### `forge sessions diff <session-id-a> <session-id-b>`

Compare two agent sessions with a structured diff.

- `<session-id-a>`: First session ID
- `<session-id-b>`: Second session ID
- Returns: Metadata comparison, transcript diff (unified), and common features

## In-Progress Commands

These commands are available but still evolving:

| Command | Status | Notes |
|---------|--------|-------|
| `forge exec` | Stable | 23 intents recognized (`cve_fix` added in v0.5.0) |
| `forge ai` | Stable | Supports both ollama and MLX backends |
| `forge serve` | Stable | 26 MCP tools |
| `forge feature` | Stable | Multi-repo git worktree management |
| `forge session` | Stable | Search, diff, handoff, transcript management |

## Natural Language Intent Map

`forge exec` and Forge MCP's `exec_nl` tool route natural language queries to forge commands using 23 intents:

| Intent | Trigger keywords | Forge command |
|--------|-----------------|---------------|
| `status` | status, state of repos, dirty repos | `forge status` |
| `dep_init` | no deps, empty deps, no dependencies | Special: runs forge scan to init deps |
| `dep_list` | what deps, dependencies, what packages | `forge deps list` |
| `dep_show` | show deps, list deps for, deps in [repo] | `forge deps list --repo [repo]` |
| `init` | init, initialize, set up | `forge init` |
| `scan` | scan, discover repos, find repos | `forge scan` |
| `health` | health, env health, dev env | `forge health` |
| `doctor` | doctor, diagnose, what's wrong | `forge doctor` |
| `config_path` | config path, where config, active config | `forge config path` |
| `config_validate` | validate config, fix config | `forge config validate --fix` |
| `cve_refresh` | cve refresh, update cve, scan vulns | `forge cve refresh` |
| `cve_list` | cve list, show vulns, vulnerabilities | `forge cve list` |
| `cve_report` | cve report, vulnerability report | `forge cve report` |
| `cve_fix` | cve fix, fix vuln, how to fix CVE | `forge cve list` (with fix info in output) |
| `feature_create` | create feature, new feature, feature branch | `forge feature create` |
| `feature_list` | list features, show features, active features | `forge feature list` |
| `decision` | log decision, record decision, add decision | `forge decision` |
| `get_decisions` | get decisions, show decisions, list decisions | `forge decision get` |
| `share_note` | share note, add note, share context | `forge share` |
| `get_notes` | get notes, show shared, what's shared | `forge share list` [Note: uses --group flag] |
| `ask` | ask, search, query workspace, find [query] | `forge ask [query]` |
| `pr_create` | create pr, open pr, make pr | `forge pr create` |
| `graph` | graph, generate graph, co-change | `forge graph` |

Intents are matched by keyword scoring with length-best-match tiebreaking. If no intent matches, the query falls through to GitHub Models free tier, then to local Ollama Gemma 4.

---

## CVE Fix Command (v0.5.0)

### `forge cve fix <vuln-id>`

Get fix information for a specific CVE or GHSA vulnerability.

```
Usage: forge cve fix <vuln-id>

Arguments:
  vuln-id    CVE identifier (e.g., CVE-2024-XXXXX or GHSA-xxxx-xxxx-xxxx)

Description:
  Queries OSV.dev for the full vulnerability detail, parses safe versions from
  affected ranges, and maps them to repos and lockfiles in your workspace.

  Shows:
  - Vulnerability summary and CVSS score
  - Safe versions per package and ecosystem
  - Affected repos and lockfiles in your workspace
  - Upgrade path recommendation
```

Example output:

```
$ forge cve fix CVE-2024-XXXXX

=== CVE-2024-XXXXX: Title ===
Summary: Description of the vulnerability
CVSS Score: 7.5 (HIGH)

Fix Versions:
  package-name@npm: 1.2.4  →  1.2.5
  (fixed in 1.2.5, introduced in 1.0.0)

Affected in your workspace:
  repo-a/package-lock.json  →  package-name@1.2.3  (upgrade to 1.2.5)
  repo-b/yarn.lock          →  package-name@1.2.2  (upgrade to 1.2.5)
```

---

**[Home](./index.md)** · **[Getting Started](./getting-started.md)** · **[Commands](./commands.md)** · **[MCP Server](./mcp.md)** · **[Architecture](./architecture.md)** · **[Comparison](./comparison.md)**
