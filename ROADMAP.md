# ws CLI Roadmap

## v0.1 — Workspace Foundation

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
- [x] CI/CD (pytest — 99 tests, CI gate before release)
- [x] Lint + typecheck (ruff, mypy)
- [ ] GitHub Pages docs site

## v0.2 — Production Workflows

**Feature completion, graphify integration, agent interoperability.**

- [x] `ws feature done <id>` — clean up worktrees + branches
- [x] `ws doctor` — diagnose workspace issues (missing repos, stale worktrees, no remotes, low disk)
- [x] `ws pr create` — create PRs across all feature repos with cross-references
- [x] graphify integration: `ws graph <repo>` — knowledge graph for any workspace repo
- [x] `ws status` with graph-aware insights
- [x] Agent install: `ws install claude` / `ws install codex` — auto-configure MCP
- [x] `ws log` — view agent session history
- [x] `ws config validate` — validate+repair workspace config
- [x] Tab completion (bash, zsh, fish)

## v0.3 — AI Integration

**Hardware-aware AI provisioning with dual backend (Ollama + MLX) and LLM-powered NL routing.**

- [x] `ws ai detect` — hardware probe (CPU, RAM, GPU, disk, Apple Silicon, MLX)
- [x] `ws ai setup` — auto-install Ollama or MLX, suggest model
- [x] `ws exec "show dirty repos"` — NL router: keyword → GitHub Models free tier → local model (Ollama/MLX) with auto-pull on demand
- [x] `ws exec --use-llm` — force LLM-based intent resolution for all queries
- [x] `ws ai status` — check whether model backend is ready for inference
- [x] `ws ai config` — view/edit AI routing config
- [x] `ws ai benchmark` — inference speed test (ollama + mlx backends)
- [x] Apple Silicon detection + MLX backend support (M1–M4 unified memory)
- [x] Dual model suggestion: Ollama (GGUF) on Intel/Linux, MLX (safetensors) on Apple Silicon
- [ ] Model routing: local ↔ BYO key ↔ GitHub Models free tier
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
