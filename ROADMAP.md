# forge CLI Roadmap

## v0.1 — Workspace Foundation

**Core CLI + MCP server for workspace operations.**

- [x] `forge init` — workspace config + GitHub auth
- [x] `forge scan` — discover git repos in ~/Workspace
- [x] `forge status [--json]` — cross-project status (branch, dirty, ahead/behind, remote state)
- [x] `forge health` — dev environment check (brew, ollama, gh, disk)
- [x] `forge clone` — clone + auto-register repos
- [x] `forge serve` — MCP stdio server with 13 tools
- [x] `forge share / forge notes` — cross-project context sharing
- [x] `forge feature create/list/worktree` — feature lifecycle with git worktrees
- [x] State model: `~/.forge/config.json`
- [x] Session artifacts: `~/.forge/sessions/<id>/`
- [x] Homebrew tap: `brew install modib/forge/forge-cli`
- [x] CI/CD (pytest — 99 tests, CI gate before release)
- [x] Lint + typecheck (ruff, mypy)
- [ ] GitHub Pages docs site

## v0.2 — Production Workflows

**Feature completion, graphify integration, agent interoperability.**

- [x] `forge feature done <id>` — clean up worktrees + branches
- [x] `forge doctor` — diagnose workspace issues (missing repos, stale worktrees, no remotes, low disk)
- [x] `forge pr create` — create PRs across all feature repos with cross-references
- [x] graphify integration: `forge graph <repo>` — knowledge graph for any workspace repo
- [x] `forge status` with graph-aware insights
- [x] Agent install: `forge install claude` / `forge install codex` — auto-configure MCP
- [x] `forge log` — view agent session history
- [x] `forge config validate` — validate+repair workspace config
- [x] Tab completion (bash, zsh, fish)

## v0.3 — AI Integration

**Hardware-aware AI provisioning with Gemma (Ollama) + Qwen (MLX) and LLM-powered NL routing.**

- [x] `forge ai detect` — hardware probe (CPU, RAM, GPU, disk, Apple Silicon, MLX)
- [x] `forge ai setup` — auto-install Ollama or MLX, suggest model
- [x] `forge exec "show dirty repos"` — NL router: keyword → GitHub Models free tier → local model (Ollama/MLX) with auto-pull on demand
- [x] `forge exec --use-llm` — force LLM-based intent resolution for all queries
- [x] `forge ai status` — check whether model backend is ready for inference
- [x] `forge ai config` — view/edit AI routing config
- [x] `forge ai benchmark` — inference speed test (ollama + mlx backends)
- [x] Apple Silicon detection + MLX backend support (M1–M4 unified memory)
- [x] Dual model suggestion: Ollama (Gemma 2B/7B GGUF) on Intel/Linux, MLX (Qwen2.5-Coder safetensors) on Apple Silicon
- [x] Model routing: local ↔ BYO key ↔ GitHub Models free tier
- [ ] Session packing: `forge session summarize <id>` → compact context

## v0.4 — Dependency Intelligence & Security

**Project awareness: deps, CVEs, semantic query. Agent handoff deferred to v0.5.**

### v0.4.0 — Rename + Dep Parsing (shipped)
- [x] Rename `ws` → `forge` (CLI, MCP, config, completions, docs)
- [x] `forge scan` parses deps from 6 ecosystems (npm, Cargo, pyproject.toml, requirements.txt, go.sum, Gemfile.lock)
- [x] `forge deps list` with `--name` and `--ecosystem` filters
- [x] `forge deps outdated` stub → migrated to `forge cve`
- [x] Config migration: `~/.forge/` primary, `~/.workspace/` fallback
- [x] 248 tests, ruff + mypy clean, CI/CD pipeline, Homebrew tap

### v0.4.1 — Config Mgmt + CVE Scanning (shipping now)
- [x] `forge config remove-repo <name>` — remove stale repos from config
- [x] `forge config validate --fix` — also purges repos with missing paths
- [x] `forge cve refresh` — query OSV.dev API for all deps
- [x] `forge cve list` — list cached CVEs with `--ecosystem`, `--min-score` filters
- [x] `forge cve describe <id>` — fetch + cache OSV.dev vulnerability details
- [x] `forge cve report` — aggregate security summary across workspace

### v0.4.2 — RAG + Gemma 4
- [ ] nomic-embed-text embeddings + FAISS vector store
- [ ] `forge ask "natural language query"` — semantic search across workspace
- [ ] Swap suggested model: Gemma 2 2B → Gemma 4 E2B (128K ctx, function calling)
- [ ] Cached CVE → RAG context for `forge ask`

## v0.5 — Agent Handoff & Dashboard

**Agents pass context. Sessions are searchable. CVE-aware agent spawning.**

- [ ] `forge cve fix <id>` — spawn agent with CVE context to auto-fix
- [ ] Agent handoff: `forge agent handoff <session-id> --to codex`
- [ ] Session search: `forge sessions search "decision about auth"`
- [ ] Session diff: `forge sessions diff <id-a> <id-b>`
- [ ] `forge dashboard` — TUI for agents, worktrees, CVEs, decisions
- [ ] GitHub issues: `forge session <id> --to-issue`

## v1.0 — Production Ready

- [ ] Stable MCP API (semver)
- [ ] Plugin system for third-party tools
- [ ] Comprehensive integration tests
- [ ] Full docs site
- [ ] Package distribution (PyPI, AUR)
