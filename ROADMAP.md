# ws CLI Roadmap

## v0.1 — Workspace Foundation (Current)

**Core CLI + MCP server for workspace operations.**

- [x] `ws init` — workspace config + GitHub auth
- [x] `ws scan` — discover git repos in ~/Workspace
- [x] `ws status [--json]` — cross-project status (branch, dirty, ahead/behind, remote state)
- [x] `ws health` — dev environment check (brew, ollama, gh, disk)
- [x] `ws clone` — clone + auto-register repos
- [x] `ws serve` — MCP stdio server with 13 tools
- [x] `ws share / ws notes` — cross-project context sharing
- [x] `ws feature create/list/worktree` — feature lifecycle with git worktrees
- [x] State model: `~/.workspace/config.json`
- [x] Session artifacts: `~/.workspace/sessions/<id>/`
- [x] Homebrew tap: `brew install modib/forge/ws-cli`
- [x] CI/CD (pytest — 86 tests, CI gate before release)
- [ ] GitHub Pages docs site
- [ ] Lint + typecheck (ruff, mypy)

## v0.2 — Production Workflows

**Feature completion, graphify integration, agent interoperability.**

- [ ] `ws feature done <id>` — clean up worktrees + branches
- [ ] `ws pr create` — create PRs across all feature repos with cross-references
- [ ] graphify integration: `ws graph <repo>` — knowledge graph for any workspace repo
- [ ] `ws status` with graph-aware insights
- [ ] Agent install: `ws install claude` / `ws install codex` — auto-configure MCP
- [ ] `ws doctor` — diagnose workspace issues (stale worktrees, missing remotes)
- [ ] `ws log` — view agent session history
- [ ] `ws config validate` — validate+repair workspace config
- [ ] JSON output for all commands (machine-readable)
- [ ] Tab completion (bash, zsh, fish)

## v0.3 — AI Integration

**Local model for NL workspace operations.**

- [ ] Hardware detection: `ws ai detect` → CPU/RAM/GPU profile
- [ ] AI provisioning: `ws ai setup` → Ollama + model install
- [ ] NL Router: `ws exec "show me dirty repos"` → 3B model → structured command
- [ ] `ws ai config` — view/edit AI routing table
- [ ] Model routing: local ↔ BYO key ↔ GitHub Models free tier
- [ ] `ws ai benchmark` — inference speed test
- [ ] Session packing: `ws session summarize <id>` → compact context

## v0.4 — Agent Handoff & Dashboard

**Agents pass context. Sessions are searchable.**

- [ ] Agent handoff: `ws agent handoff <session-id> --to codex`
- [ ] Session search: `ws sessions search "decision about auth"`
- [ ] Session diff: `ws sessions diff <id-a> <id-b>`
- [ ] `ws dashboard` — TUI for agents, worktrees, decisions
- [ ] Decision broadcasting between sibling worktrees
- [ ] GitHub issues: `ws session <id> --to-issue`

## v0.5 — Ambient Intelligence

**Proactive workspace monitoring.**

- [ ] `ws watch` — daemon for workspace state changes
- [ ] Error pattern detection (repeated test failures, build errors)
- [ ] Health regression alerts (disk, model, git divergence)
- [ ] Predictive worktree suggestions
- [ ] Status notifications in terminal

## v1.0 — Production Ready

- [ ] Stable MCP API (semver)
- [ ] Plugin system for third-party tools
- [ ] Comprehensive integration tests
- [ ] Full docs site
- [ ] Package distribution (PyPI, AUR)
