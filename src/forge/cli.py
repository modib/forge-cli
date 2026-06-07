import argparse
import os
import subprocess
import sys
from . import config as cfg
from . import engine
from . import git
from . import graph as forgegraph
from . import install as forgeinstall
from . import ai as forgeai
from . import deps as forge_deps
from . import cve as forge_cve


def cmd_init(args):
    c = engine.init_workspace(provider=args.provider)
    print(f"Initialized workspace at {cfg.WORKSPACE_DIR}")
    print(f"Workspace root: {c.get('workspace_root')}")
    print(f"Providers: {', '.join(c.get('providers', {}).keys())}")


def cmd_scan(args):
    added, total = engine.scan_workspace()
    print(f"Scanned {total} repos in {cfg.WORKSPACE_ROOT}")
    if added:
        print(f"Added {len(added)} new repos:")
        for name in added:
            print(f"  + {name}")
    else:
        print("No new repos found (all already registered)")
    c = cfg.load_config()
    total_deps = 0
    for repo in c.get("repos", []):
        deps = forge_deps.update_deps_for_repo(repo["name"], repo["path"])
        total_deps += len(deps)
    print(f"Parsed {total_deps} dependencies across {total} repos")


def cmd_status(args):
    if args.json:
        status = engine.get_overall_status()
        import json
        print(json.dumps(status, indent=2, default=str))
        return

    status = engine.get_overall_status()
    total = status["total_repos"]
    print(f"Workspace: {cfg.WORKSPACE_ROOT}")
    print(f"Repos: {total} total")
    parts = []
    if status["dirty"]:
        parts.append(f"{status['dirty']} dirty")
    if status["ahead"]:
        parts.append(f"{status['ahead']} ahead")
    if status["behind"]:
        parts.append(f"{status['behind']} behind")
    if status["missing"]:
        parts.append(f"{status['missing']} missing")
    if parts:
        print(f"  ({', '.join(parts)})")
    print()

    for r in status["repos"]:
        exists = r.get("exists", False)
        name = r["name"]
        if not exists:
            print(f"  \033[31m✗ {name}\033[0m  ({r.get('error', 'missing')})")
            continue
        error = r.get("error")
        if error:
            print(f"  \033[33m⚠ {name}\033[0m  ({error})")
            continue
        branch = r.get("branch", "?")
        dirty_mark = " \033[33m●\033[0m" if r.get("dirty") else ""
        ahead_behind = ""
        if r.get("ahead", 0) > 0 or r.get("behind", 0) > 0:
            ahead_behind = f" \033[32m+{r['ahead']}\033[0m/\033[31m-{r['behind']}\033[0m"

        has_remote = r.get("has_remote", False)
        remote_url = r.get("remote_url", "")
        has_upstream = r.get("has_upstream", False)
        if has_remote and remote_url:
            d = git.sanitize_url(remote_url)
            if d.endswith(".git"):
                d = d[:-4]
            remote_str = f"  \033[36m⇄\033[0m {d}"
            if not has_upstream:
                remote_str += " \033[90m(no tracking)\033[0m"
        elif has_remote:
            remote_str = f"  \033[36m⇄\033[0m {r['remote_name']} \033[90m(no url)\033[0m"
        else:
            remote_str = "  \033[90m○\033[0m"

        last = r.get("last_commit_msg", "")
        if len(last) > 50:
            last = last[:47] + "..."
        print(f"  {name}{dirty_mark}  \033[36m{branch}\033[0m{ahead_behind}{remote_str}")
        if last:
            print(f"    {last}")

    if args.graph:
        dirty_map = {r["name"]: r.get("path", "") for r in status["repos"] if r.get("dirty") and r.get("exists") and r.get("path")}
        if dirty_map:
            impacts = forgegraph.cross_repo_impact(dirty_map)
            if impacts:
                print("\n\033[36mCross-repo impact:\033[0m")
                for imp in impacts:
                    print(f"  {imp['repo_a']} ↔ {imp['repo_b']}  (\033[33m{imp['shared_count']} shared files\033[0m)")
                    for f in imp["shared_files"][:5]:
                        print(f"    {f}")
                    if len(imp["shared_files"]) > 5:
                        print(f"    ... and {len(imp['shared_files']) - 5} more")

    features = status.get("active_features", 0)
    if features:
        print(f"\nActive features: {features}")
    if status.get("active_sessions"):
        print(f"Active sessions: {status['active_sessions']}")


def cmd_clone(args):
    url = args.url
    name = args.name
    target = cfg.WORKSPACE_ROOT
    if not name:
        name = url.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
    result = git.clone(url, target, name)
    if result.startswith("error"):
        print(f"\033[31m{result}\033[0m", file=sys.stderr)
        sys.exit(1)
    print(f"Cloned to {result}")
    repo = {
        "name": name,
        "path": os.path.join(target, name),
        "provider": git._detect_provider(url),
        "url": url,
        "default_branch": "main",
    }
    c = cfg.load_config()
    cfg.add_repo(c, repo)
    cfg.save_config(c)
    print(f"Registered {name} in workspace config")


def cmd_doctor(args):
    d = engine.diagnose()
    if args.json:
        import json
        print(json.dumps(d, indent=2, default=str))
        return
    if not d["issues"]:
        print("\033[32mWorkspace looks healthy\033[0m")
        return
    print(f"Found {d['total_issues']} issue(s):\n")
    for issue in d["issues"]:
        sev = issue["severity"]
        if sev == "error":
            marker = "\033[31m✗\033[0m"
        elif sev == "warning":
            marker = "\033[33m⚠\033[0m"
        else:
            marker = "\033[36mi\033[0m"
        label = f" [{issue['repo']}]" if "repo" in issue else ""
        label += f" [{issue['feature']}]" if "feature" in issue else ""
        print(f"  {marker}{label} {issue['detail']}")


def cmd_health(args):
    h = engine.health_check()
    print("Dev Environment Health")
    print("---------------------")
    for tool, ok in [("brew", "✓"), ("ollama", "✓"), ("gh", "✓"),
                     ("python3", "✓"), ("node", "✓"), ("npm", "✓")]:
        available = h.get(tool, False)
        mark = "\033[32m✓\033[0m" if available else "\033[31m✗\033[0m"
        print(f"  {mark} {tool}")
    gh_auth = h.get("gh_auth", False)
    mark = "\033[32m✓\033[0m" if gh_auth else "\033[31m✗\033[0m"
    print(f"  {mark} gh auth")
    print(f"\nDisk: {h.get('disk_used_pct', '?')}% used "
          f"({h.get('disk_free_gb', '?')} GB free of {h.get('disk_total_gb', '?')} GB)")


def cmd_feature(args):
    action = args.action
    if action == "create":
        repos = args.repos.split(",") if args.repos else []
        feat = engine.add_feature(args.name, repos=repos)
        print(f"Created feature: {feat['id']}")
        print(f"  Name: {feat['name']}")
        print(f"  Repos: {', '.join(feat['repos']) if feat['repos'] else '(none yet)'}")
        print(f"  Use: forge feature worktree {feat['id']} <repo>")
    elif action == "list":
        features = engine.list_features()
        if not features:
            print("No features")
            return
        for f in features:
            print(f"  {f['id']}: {f['name']} ({len(f.get('worktrees', {}))} worktrees)")
    elif action == "worktree":
        fname = args.name
        repo_name = args.repo
        c = cfg.load_config()
        feature = None
        for f in c.get("features", []):
            if f["id"] == fname or f["name"] == fname:
                feature = f
                break
        if not feature:
            print(f"Feature not found: {fname}")
            return
        if not repo_name:
            print(f"Repos in feature '{feature['name']}': {', '.join(feature.get('repos', []))}")
            return
        repo = cfg.repo_by_name(c, repo_name)
        if not repo:
            print(f"Repo not found: {repo_name}")
            return
        worktrees_dir = os.path.join(cfg.WORKSPACE_DIR, "..", ".workspaces", fname)
        os.makedirs(worktrees_dir, exist_ok=True)
        branch = f"feature/{fname}"
        result = subprocess.run(
            ["git", "worktree", "add", "-b", branch, os.path.join(worktrees_dir, repo_name), "HEAD"],
            cwd=repo["path"], capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"Worktree error: {result.stderr.strip() or result.stdout.strip()}")
            return
        feature.setdefault("worktrees", {})[repo_name] = os.path.join(worktrees_dir, repo_name)
        cfg.save_config(c)
        print(f"Created worktree for {repo_name} at {os.path.join(worktrees_dir, repo_name)}")
    elif action == "done":
        result = engine.complete_feature(args.name)
        if "error" in result:
            print(f"\033[31m{result['error']}\033[0m")
            return
        print(f"Completed feature: \033[36m{result['name']}\033[0m ({result['id']})")
        if result["removed_worktrees"]:
            print(f"  Removed worktrees: {', '.join(result['removed_worktrees'])}")
        if result["failed_worktrees"]:
            print(f"  \033[33mFailed to remove: {', '.join(result['failed_worktrees'])}\033[0m")
        print("  Feature removed from workspace config")
    else:
        print(f"Unknown feature command: {action}")


def cmd_share(args):
    c = cfg.load_config()
    groups = c.setdefault("groups", [])
    group_name = args.group or "default"
    group = None
    for g in groups:
        if g["name"] == group_name:
            group = g
            break
    if not group:
        group = {"name": group_name, "repos": [], "notes": []}
        groups.append(group)
    group.setdefault("notes", []).append({
        "content": args.content,
        "label": args.label or "",
        "timestamp": cfg.now_iso(),
    })
    cfg.save_config(c)
    print(f"Shared note in group '{group_name}'")


def cmd_notes(args):
    c = cfg.load_config()
    group_name = args.group or "default"
    for g in c.get("groups", []):
        if g["name"] == group_name:
            notes = g.get("notes", [])
            if not notes:
                print(f"No notes in group '{group_name}'")
                return
            for n in notes:
                label = f" [{n.get('label')}]" if n.get("label") else ""
                ts = n.get("timestamp", "").split(".")[0].replace("T", " ")
                print(f"  {ts}{label}")
                print(f"    {n['content']}")
            return
    print(f"Group not found: {group_name}")


def cmd_graph(args):
    import json as j
    result = forgegraph.generate_graph(args.name, graph_type=args.type, depth=args.depth)
    if "error" in result:
        print(f"\033[31m{result['error']}\033[0m")
        return
    if args.format == "json":
        print(j.dumps(result, indent=2, default=str))
    elif args.format == "text":
        print(f"Graph: \033[36m{result['repo']}\033[0m ({args.type})")
        if args.type == "co-change":
            edges_out = []
            for e in result.get("edges", []):
                if e["weight"] > 1:
                    edges_out.append(f"  {e['source']} <-> {e['target']}  (\033[33m{e['weight']}x\033[0m)")
                else:
                    edges_out.append(f"  {e['source']} <-> {e['target']}")
            if edges_out:
                print("Co-change relationships:")
                print("\n".join(edges_out[:20]))
                if len(edges_out) > 20:
                    print(f"  ... and {len(edges_out) - 20} more")
            print(f"\nFiles tracked: {len(result.get('nodes', []))}")
            print(f"Relationships: {len(result.get('edges', []))}")
        elif args.type == "branches":
            branches = result.get("branches", [])
            current = result.get("current", "")
            for b in branches:
                mark = "\033[32m*\033[0m " if b == current else "  "
                is_remote = "(remote)" if b.startswith("remotes/") else ""
                print(f"  {mark}{b} {is_remote}")
            if result.get("history"):
                print(f"\nRecent history:\n{result['history']}")
    else:
        print(f"Unknown format: {args.format}")


def cmd_log(args):
    import json as j
    if args.name:
        result = engine.get_session(args.name)
        if "error" in result:
            print(f"\033[31m{result['error']}\033[0m")
            return
        if args.json:
            print(j.dumps(result, indent=2, default=str))
            return
        s = result["session"]
        print(f"Session: \033[36m{s['id']}\033[0m")
        print(f"  Agent:   {s.get('agent', '?')}")
        print(f"  Started: {s.get('started', '?')}")
        if s.get("feature"):
            print(f"  Feature: {s['feature']}")
        if s.get("context"):
            print(f"  Context: {s['context'][:200]}")
        if result.get("transcript"):
            lines = result["transcript"].split("\n")
            print(f"\n  Transcript ({len(lines)} lines):")
            for line in lines[:30]:
                print(f"    {line}")
            if len(lines) > 30:
                print(f"    ... ({len(lines) - 30} more lines)")
    else:
        sessions = engine.list_sessions(limit=args.limit)
        if args.json:
            print(j.dumps(sessions, indent=2, default=str))
            return
        if not sessions:
            print("No sessions found")
            return
        print(f"Recent sessions (last {len(sessions)}):\n")
        for s in sessions:
            ctx = f" — {s['context_preview']}" if s.get("context_preview") else ""
            feat = f" [{s['feature']}]" if s.get("feature") else ""
            print(f"  \033[36m{s['id']}\033[0m  {s['agent']}{feat}  \033[90m{s.get('started', '')}\033[0m{ctx}")


def cmd_install(args):
    result = forgeinstall.install_agent(args.agent)
    if "error" in result:
        print(f"\033[31m{result['error']}\033[0m")
        return
    if result.get("success"):
        note = result.get("note", "")
        print(f"\033[32m✓\033[0m {note}")
        print(f"  Binary: \033[36m{result.get('binary', '?')}\033[0m")
        if result.get("mcp_config"):
            print(f"  MCP config: {result['mcp_config']}")
        if result.get("env_config"):
            print(f"  Env config: {result['env_config']}")


def cmd_pr(args):
    action = args.action
    if action == "create":
        result = engine.create_prs(args.name, title=args.title, body=args.body, draft=args.draft)
        if "error" in result:
            print(f"\033[31m{result['error']}\033[0m")
            return
        print(f"Feature: \033[36m{result['feature']}\033[0m ({result['id']})")
        for p in result["prs"]:
            if p.get("status") == "created":
                url_str = f" \033[32m{p['url']}\033[0m"
                xref = " \033[90m(cross-ref'd)\033[0m" if p.get("cross_referenced") else ""
                print(f"  \033[32m✓\033[0m {p['repo']}{url_str}{xref}")
            elif "error" in p:
                print(f"  \033[31m✗\033[0m {p['repo']}  \033[33m{p['error']}\033[0m")
    else:
        print(f"Unknown pr command: {action}")


def cmd_completion(args):
    shell = args.shell
    script = _completion_script(shell)
    print(script)


def _completion_script(shell):
    if shell == "bash":
        return '''_forge_completions() {
    local cur prev words cword
    _init_completion || return

    local subcmds="init scan status clone health doctor feature graph install log notes pr share serve config deps cve completion"
    local feature_actions="create list worktree done"
    local pr_actions="create"
    local install_agents="claude codex"
    local graph_types="co-change branches"
    local graph_formats="json text"
    local config_actions="path validate remove-repo"

    if [[ $cword -eq 1 ]]; then
        COMPREPLY=($(compgen -W "$subcmds" -- "$cur"))
        return
    fi

    case ${words[1]} in
        init)
            COMPREPLY=($(compgen -W "--provider" -- "$cur"))
            ;;
        status)
            COMPREPLY=($(compgen -W "--json --graph $(forge config path 2>/dev/null && forge status 2>/dev/null | grep -oP '^  \\K\\w+' || true)" -- "$cur"))
            ;;
        clone)
            COMPREPLY=($(compgen -W "--name" -- "$cur"))
            ;;
        doctor)
            COMPREPLY=($(compgen -W "--json" -- "$cur"))
            ;;
        feature)
            if [[ $cword -eq 2 ]]; then
                COMPREPLY=($(compgen -W "$feature_actions" -- "$cur"))
            elif [[ $cword -ge 3 && ${words[2]} == "create" ]]; then
                COMPREPLY=($(compgen -W "--repos" -- "$cur"))
            elif [[ $cword -ge 3 && ${words[2]} == "worktree" ]]; then
                COMPREPLY=($(compgen -W "--repo $(forge config path 2>/dev/null && forge feature list 2>/dev/null | grep -oP '^  \\K\\w+' || true)" -- "$cur"))
            fi
            ;;
        graph)
            COMPREPLY=($(compgen -W "--type --format --depth $(forge config path 2>/dev/null && forge status 2>/dev/null | grep -oP '^  \\K\\w+' || true)" -- "$cur"))
            if [[ "$prev" == "--type" ]]; then
                COMPREPLY=($(compgen -W "$graph_types" -- "$cur"))
            elif [[ "$prev" == "--format" ]]; then
                COMPREPLY=($(compgen -W "$graph_formats" -- "$cur"))
            fi
            ;;
        install)
            COMPREPLY=($(compgen -W "$install_agents" -- "$cur"))
            ;;
        pr)
            if [[ $cword -eq 2 ]]; then
                COMPREPLY=($(compgen -W "$pr_actions" -- "$cur"))
            elif [[ $cword -ge 3 && ${words[2]} == "create" ]]; then
                COMPREPLY=($(compgen -W "--title --body --draft" -- "$cur"))
            fi
            ;;
        config)
            COMPREPLY=($(compgen -W "$config_actions --fix" -- "$cur"))
            ;;
        cve)
            COMPREPLY=($(compgen -W "refresh list describe report --ecosystem --min-score" -- "$cur"))
            ;;
        share)
            COMPREPLY=($(compgen -W "--group --label" -- "$cur"))
            ;;
        notes)
            COMPREPLY=($(compgen) -- "$cur")
            ;;
        log)
            COMPREPLY=($(compgen -W "--limit --json" -- "$cur"))
            ;;
        completion)
            COMPREPLY=($(compgen -W "bash zsh fish" -- "$cur"))
            ;;
    esac
} &&
complete -F _forge_completions forge
'''
    elif shell == "zsh":
        return '''#compdef forge

_forge() {
    local line state

    _arguments -C \\
        "--version[Show version]" \\
        "1: :->cmds" \\
        "*::arg:->args"

    case $state in
        cmds)
            _values "command" \\
                "init[Initialize workspace config]" \\
                "scan[Discover repos in workspace root]" \\
                "status[Show workspace status]" \\
                "clone[Clone a repo into workspace]" \\
                "health[Check dev environment health]" \\
                "doctor[Diagnose workspace issues]" \\
                "feature[Manage features]" \\
                "graph[Generate knowledge graph for a repo]" \\
                "install[Install and configure AI agents]" \\
                "log[View agent session history]" \\
                "notes[List shared notes]" \\
                "pr[Manage pull requests]" \\
                "share[Share a note across projects]" \\
                "serve[Start MCP server (stdio)]" \\
                "config[Manage workspace configuration]" \\
                "deps[Manage project dependencies]" \\
                "cve[CVE vulnerability scanning]" \\
                "completion[Generate shell completion scripts]"
            ;;
        args)
            case $words[1] in
                init)
                    _arguments "--provider[Auth provider]:(github gitlab)"
                    ;;
                status)
                    _arguments "--json[Output as JSON]" "--graph[Show cross-repo impact]"
                    _forge_repos
                    ;;
                clone)
                    _arguments "--name[Override repo name]:"
                    ;;
                doctor)
                    _arguments "--json[Output as JSON]"
                    ;;
                feature)
                    _arguments "1:action:(create list worktree done)" \\
                        "2: :_forge_features" \\
                        "--repos[Comma-separated repo names]:" \\
                        "--repo[Repo name for worktree]:"
                    ;;
                graph)
                    _arguments "1: :_forge_repos" \\
                        "--type[Graph type]:(co-change branches)" \\
                        "--format[Output format]:(json text)" \\
                        "--depth[Commits to analyze]:"
                    ;;
                install)
                    _arguments "1:agent:(claude codex)"
                    ;;
                log)
                    _arguments "--limit[Max sessions]:" "--json[Output as JSON]"
                    ;;
                pr)
                    _arguments "1:action:(create)" \\
                        "2: :_forge_features" \\
                        "--title[PR title]:" \\
                        "--body[PR body]:" \\
                        "--draft[Create as draft PR]"
                    ;;
                share)
                    _arguments "--group[Group name]:" "--label[Optional label]:"
                    ;;
                config)
                    _arguments "1:action:(path validate remove-repo)" "--fix[Auto-repair fixable issues]"
                    ;;
                cve)
                    _arguments "1:action:(refresh list describe report)" \\
                        "--ecosystem[Filter by ecosystem]:" \\
                        "--min-score[Minimum CVSS score]:" \\
                        "--refresh[Re-fetch details from OSV.dev]"
                    ;;
                completion)
                    _arguments "1:shell:(bash zsh fish)"
                    ;;
            esac
            ;;
    esac
}

_forge_repos() {
    local -a repos
    if [[ -f ~/.forge/config.json ]]; then
        repos=(${(f)"$(command forge status --json 2>/dev/null | command python3 -c \"import sys,json; d=json.load(sys.stdin); [print(r['name']) for r in d.get('repos',[])]\" 2>/dev/null)"})
    fi
    _values 'repos' $repos
}

_forge_features() {
    local -a features
    if [[ -f ~/.forge/config.json ]]; then
        features=(${(f)"$(command forge config path 2>/dev/null && command forge feature list 2>/dev/null | command grep -oP '^  \\K\\w+' 2>/dev/null || true)"})
    fi
    _values 'features' $features
}

_forge "$@"
'''
    elif shell == "fish":
        return '''function _forge_completions
    set -l cmds init scan status clone health doctor feature graph install log notes pr share serve config deps cve completion

    # Top-level commands
    complete -c forge -f
    for cmd in $cmds
        complete -c forge -n "not __fish_seen_subcommand_from $cmds" -a $cmd
    end

    # init
    complete -c forge -n "__fish_seen_subcommand_from init" -l provider -xa "github gitlab"

    # status
    complete -c forge -n "__fish_seen_subcommand_from status" -l json
    complete -c forge -n "__fish_seen_subcommand_from status" -l graph
    complete -c forge -n "__fish_seen_subcommand_from status" -xa "(__forge_repos)"

    # clone
    complete -c forge -n "__fish_seen_subcommand_from clone" -l name -r

    # doctor
    complete -c forge -n "__fish_seen_subcommand_from doctor" -l json

    # feature
    complete -c forge -n "__fish_seen_subcommand_from feature; and not __fish_seen_subcommand_from create list worktree done" -xa "create list worktree done"
    complete -c forge -n "__fish_seen_subcommand_from feature; and __fish_seen_subcommand_from create" -l repos -r
    complete -c forge -n "__fish_seen_subcommand_from feature; and __fish_seen_subcommand_from worktree" -l repo -r
    complete -c forge -n "__fish_seen_subcommand_from feature; and __fish_seen_subcommand_from worktree" -xa "(__forge_features)"

    # graph
    complete -c forge -n "__fish_seen_subcommand_from graph" -l type -xa "co-change branches"
    complete -c forge -n "__fish_seen_subcommand_from graph" -l format -xa "json text"
    complete -c forge -n "__fish_seen_subcommand_from graph" -l depth -r
    complete -c forge -n "__fish_seen_subcommand_from graph" -xa "(__forge_repos)"

    # install
    complete -c forge -n "__fish_seen_subcommand_from install" -xa "claude codex"

    # log
    complete -c forge -n "__fish_seen_subcommand_from log" -l limit -r
    complete -c forge -n "__fish_seen_subcommand_from log" -l json

    # pr
    complete -c forge -n "__fish_seen_subcommand_from pr; and not __fish_seen_subcommand_from create" -xa "create"
    complete -c forge -n "__fish_seen_subcommand_from pr; and __fish_seen_subcommand_from create" -l title -r
    complete -c forge -n "__fish_seen_subcommand_from pr; and __fish_seen_subcommand_from create" -l body -r
    complete -c forge -n "__fish_seen_subcommand_from pr; and __fish_seen_subcommand_from create" -l draft
    complete -c forge -n "__fish_seen_subcommand_from pr; and __fish_seen_subcommand_from create" -xa "(__forge_features)"

    # share
    complete -c forge -n "__fish_seen_subcommand_from share" -l group -r
    complete -c forge -n "__fish_seen_subcommand_from share" -l label -r

    # config
    complete -c forge -n "__fish_seen_subcommand_from config; and not __fish_seen_subcommand_from path validate remove-repo" -xa "path validate remove-repo"
    complete -c forge -n "__fish_seen_subcommand_from config; and __fish_seen_subcommand_from validate" -l fix

    # cve
    complete -c forge -n "__fish_seen_subcommand_from cve; and not __fish_seen_subcommand_from refresh list describe report" -xa "refresh list describe report"
    complete -c forge -n "__fish_seen_subcommand_from cve; and __fish_seen_subcommand_from list report" -l ecosystem -r
    complete -c forge -n "__fish_seen_subcommand_from cve; and __fish_seen_subcommand_from list report" -l min-score -r
    complete -c forge -n "__fish_seen_subcommand_from cve; and __fish_seen_subcommand_from describe" -l refresh

    # completion
    complete -c forge -n "__fish_seen_subcommand_from completion" -xa "bash zsh fish"
end

function __forge_repos
    if test -f ~/.forge/config.json
        command forge status --json 2>/dev/null | command python3 -c "import sys,json; d=json.load(sys.stdin); [print(r['name']) for r in d.get('repos',[])]" 2>/dev/null
    end
end

function __forge_features
    if test -f ~/.forge/config.json
        command forge feature list 2>/dev/null | grep -oP '^  \\K\\w+' 2>/dev/null || true
    end
end
'''
    else:
        return f"echo 'Unsupported shell: {shell}'"


def cmd_ai(args):
    action = args.action
    if action == "detect":
        forgeai.detect_and_print(args)
    elif action == "config":
        forgeai.ai_config_cmd(args)
    elif action == "status":
        ready = forgeai.check_model_ready(backend=args.backend)
        if ready.get("ready"):
            print("\033[32m✓\033[0m Model ready")
            print(f"  Backend: \033[36m{ready['backend']}\033[0m")
            print(f"  Model:   \033[36m{ready.get('model', '?')}\033[0m")
            if ready.get("note"):
                print(f"  Note:    {ready['note']}")
        else:
            print("\033[31m✗\033[0m Model not ready")
            print(f"  {ready.get('error', 'Unknown issue')}")
    elif action == "setup":
        result = forgeai.setup(backend=args.backend, model=args.model)
        if "error" in result:
            print(f"\033[31m{result['error']}\033[0m")
        else:
            for line in result.get("log", []):
                print(line)
            b = result.get("backend", "ollama")
            if result.get("ollama_installed"):
                print("\033[32m✓\033[0m Ollama installed")
            if result.get("mlx_installed"):
                print("\033[32m✓\033[0m MLX installed")
            if result.get("model"):
                print(f"\033[32m✓\033[0m {b} configured — suggested model: {result['model']}")
    elif action == "benchmark":
        result = forgeai.benchmark_model(model=args.model, prompt=args.prompt, backend=args.backend)
        if "error" in result:
            print(f"\033[31m{result['error']}\033[0m")
        else:
            print(f"Backend: \033[36m{result.get('backend', '?')}\033[0m")
            print(f"Model: \033[36m{result['model']}\033[0m")
            print(f"Prompt: {result['prompt'][:80]}...")
            print(f"Response length: {result['response_length']} chars")
            print(f"Latency: \033[33m{result['latency_ms']}ms\033[0m")
            print(f"Tokens/sec: \033[33m{result['tokens_per_sec']}\033[0m")


def cmd_deps(args):
    action = args.action
    if action == "list":
        cmd_deps_list(args)
    elif action == "outdated":
        cmd_deps_outdated(args)


def cmd_exec(args):
    query = args.query
    result = forgeai.exec_nl(query, dry_run=args.dry_run)
    if "error" in result:
        print(f"\033[31m{result['error']}\033[0m")
        return
    resolved_by = result.get("resolved_by", "")
    if resolved_by and resolved_by != "keyword":
        print(f"\033[90mforge: resolved by {resolved_by}\033[0m", file=sys.stderr)
    if args.dry_run:
        print(f"\033[36mIntent:\033[0m {result.get('intent', '?')}")
        print(f"\033[36mCommand:\033[0m {result.get('command', '?')}")
        return
    print(f"\033[90m$ {result.get('command', '')}\033[0m")
    if result.get("output"):
        print(result["output"])


def cmd_deps_list(args):
    deps = forge_deps.list_deps(repo_name=args.name, ecosystem=args.ecosystem)
    if not deps:
        print("No dependencies found")
        return
    print(f"Dependencies ({len(deps)} total):")
    for d in deps:
        eco = d["ecosystem"]
        ver = d["version"] or "*"
        name = d["name"]
        print(f"  \033[36m{eco}\033[0m  {name}  \033[90m{ver}\033[0m")


def cmd_deps_outdated(args):
    print("Use: forge cve list --min-score 0")
    print("  or: forge cve report")


def cmd_cve(args):
    action = args.action
    if action == "refresh":
        result = forge_cve.refresh()
        print(f"Queried {result['queried']} packages")
        print(f"Found {result['vulns_found']} new vulnerabilities")
        print(f"Total cached: {result['total_cached']}")
    elif action == "list":
        cves = forge_cve.list_cves(
            repo_name=args.name,
            ecosystem=args.ecosystem,
            min_score=args.min_score,
        )
        if not cves:
            print("No CVEs found")
            return
        print(f"CVEs ({len(cves)} total):")
        for v in cves:
            score = v.get("cvss_score")
            score_str = f"  \033[33m{score:.1f}\033[0m" if score is not None else "  \033[90m? \033[0m"
            summary = v.get("summary", "")
            if len(summary) > 60:
                summary = summary[:57] + "..."
            print(f"  \033[36m{v['id']}\033[0m{score_str}  {v['package']}@{v['version']}  \033[90m{summary}\033[0m")
    elif action == "describe":
        result = forge_cve.describe(args.vuln_id, refresh_cache=args.refresh)
        if result is None:
            print(f"\033[31mCould not fetch details for {args.vuln_id}\033[0m")
            return
        print(f"\033[36m{result['id']}\033[0m")
        if result.get("summary"):
            print(f"  Summary: {result['summary']}")
        if result.get("cvss_score") is not None:
            print(f"  CVSS:    \033[33m{result['cvss_score']:.1f}\033[0m")
        if result.get("aliases"):
            print(f"  Aliases: {', '.join(result['aliases'])}")
    elif action == "report":
        result = forge_cve.report(
            repo_name=args.name,
            ecosystem=args.ecosystem,
            min_score=args.min_score,
        )
        print("\033[36mSecurity Report\033[0m")
        print(f"  Total CVEs:      {result['total']}")
        if result["total"] == 0:
            print("\033[32m  No vulnerabilities found\033[0m")
            return
        sev = result["by_severity"]
        print(f"  Critical:        {sev['critical']}")
        print(f"  High:            {sev['high']}")
        print(f"  Moderate:        {sev['moderate']}")
        print(f"  Low:             {sev['low']}")
        print(f"  Unknown:         {sev['unknown']}")
        if result["top_packages"]:
            print("\n  Top affected packages:")
            for pkg, count in result["top_packages"]:
                print(f"    {pkg}  ({count})")


def cmd_serve(args):
    import asyncio
    from .server import run_server
    asyncio.run(run_server())


def cmd_config_path(args):
    if args.sub == "validate":
        result = engine.validate_config(fix=args.fix)
        if result["valid"]:
            print("\033[32mConfig is valid\033[0m")
        else:
            print("\033[31mConfig has errors\033[0m")
        for issue in result["issues"]:
            sev = issue["severity"]
            if sev == "error":
                marker = "\033[31m✗\033[0m"
            elif sev == "warning":
                marker = "\033[33m⚠\033[0m"
            else:
                marker = "\033[36mi\033[0m"
            label = f" [{issue.get('repo', '')}]" if issue.get("repo") else ""
            label += f" [{issue.get('feature', '')}]" if issue.get("feature") else ""
            print(f"  {marker}{label} {issue['detail']}")
        if args.fix and result.get("_repaired"):
            print("\n\033[32mRepaired:\033[0m")
            for r in result["_repaired"]:
                print(f"  \033[32m✓\033[0m {r}")
    elif args.sub == "remove-repo":
        cmd_config_remove_repo(args)
    else:
        print(cfg.CONFIG_PATH)


def cmd_config_remove_repo(args):
    if not args.name:
        print("\033[31mUsage: forge config remove-repo <name>\033[0m")
        return
    c = cfg.load_config()
    repo = cfg.repo_by_name(c, args.name)
    if not repo:
        print(f"\033[31mRepo not found: {args.name}\033[0m")
        return
    cfg.remove_repo(c, args.name)
    cfg.save_config(c)
    print(f"\033[32mRemoved {args.name} from config\033[0m")


def main():
    parser = argparse.ArgumentParser(prog="forge", description="Forge CLI")
    parser.add_argument("--version", action="store_true", help="Show version")

    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Initialize workspace config")
    p_init.add_argument("--provider", choices=["github", "gitlab"], help="Auth provider")

    sub.add_parser("scan", help="Discover repos in workspace root")

    p_status = sub.add_parser("status", help="Show workspace status")
    p_status.add_argument("name", nargs="?", help="Show status for a specific repo")
    p_status.add_argument("--json", action="store_true", help="Output as JSON")
    p_status.add_argument("--graph", action="store_true", help="Show cross-repo graph impact insights")

    p_clone = sub.add_parser("clone", help="Clone a repo into workspace")
    p_clone.add_argument("url", help="Repository URL")
    p_clone.add_argument("--name", "-n", help="Override repo name")

    sub.add_parser("health", help="Check dev environment health")

    p_doctor = sub.add_parser("doctor", help="Diagnose workspace issues")
    p_doctor.add_argument("--json", action="store_true", help="Output as JSON")

    p_feat = sub.add_parser("feature", help="Manage features")
    p_feat.add_argument("action", choices=["create", "list", "worktree", "done"], help="Feature action")
    p_feat.add_argument("name", nargs="?", help="Feature name")
    p_feat.add_argument("--repos", "-r", help="Comma-separated repo names")
    p_feat.add_argument("--repo", help="Repo name for worktree command")

    p_share = sub.add_parser("share", help="Share a note across projects")
    p_share.add_argument("content", help="Note content")
    p_share.add_argument("--group", "-g", default="default", help="Group name")
    p_share.add_argument("--label", "-l", help="Optional label")

    p_notes = sub.add_parser("notes", help="List shared notes")
    p_notes.add_argument("group", nargs="?", default="default", help="Group name")

    sub.add_parser("serve", help="Start MCP server (stdio)")

    p_log = sub.add_parser("log", help="View agent session history")
    p_log.add_argument("name", nargs="?", help="Session ID to view details")
    p_log.add_argument("--limit", type=int, default=10, help="Max sessions to list")
    p_log.add_argument("--json", action="store_true", help="Output as JSON")

    p_install = sub.add_parser("install", help="Install and configure AI agents")
    p_install.add_argument("agent", choices=["claude", "codex"], help="Agent to install")

    p_graph = sub.add_parser("graph", help="Generate knowledge graph for a repo")
    p_graph.add_argument("name", help="Repository name")
    p_graph.add_argument("--type", choices=["co-change", "branches"], default="co-change", help="Graph type")
    p_graph.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
    p_graph.add_argument("--depth", type=int, default=50, help="Commits to analyze (default: 50)")

    p_pr = sub.add_parser("pr", help="Manage pull requests")
    p_pr.add_argument("action", choices=["create"])
    p_pr.add_argument("name", help="Feature name or ID")
    p_pr.add_argument("--title", help="PR title (default: 'Feature: <name>')")
    p_pr.add_argument("--body", help="PR body text")
    p_pr.add_argument("--draft", action="store_true", help="Create as draft PR")

    p_config = sub.add_parser("config", help="Manage workspace configuration")
    p_config.add_argument("sub", nargs="?", default="path", choices=["path", "validate", "remove-repo"])
    p_config.add_argument("--fix", action="store_true", help="Auto-repair fixable issues")
    p_config.add_argument("name", nargs="?", help="Repository name (for remove-repo)")

    p_deps = sub.add_parser("deps", help="Manage project dependencies")
    p_deps.add_argument("action", choices=["list", "outdated"], help="Dependency action")
    p_deps.add_argument("name", nargs="?", help="Repository name (omit for all)")
    p_deps.add_argument("--ecosystem", "-e", help="Filter by ecosystem (npm, cargo, pypi, go, rubygems)")

    p_cve = sub.add_parser("cve", help="CVE vulnerability scanning")
    p_cve.add_argument("action", choices=["refresh", "list", "describe", "report"], help="CVE action")
    p_cve.add_argument("name", nargs="?", help="Repository name (omit for all)")
    p_cve.add_argument("vuln_id", nargs="?", help="Vulnerability ID (for describe)")
    p_cve.add_argument("--ecosystem", "-e", help="Filter by ecosystem")
    p_cve.add_argument("--min-score", type=float, default=None, help="Minimum CVSS score filter")
    p_cve.add_argument("--refresh", action="store_true", help="Re-fetch details from OSV.dev")

    p_completion = sub.add_parser("completion", help="Generate shell completion script")
    p_completion.add_argument("shell", choices=["bash", "zsh", "fish"], help="Shell type")

    p_ai = sub.add_parser("ai", help="AI integration commands (detect, status, setup, config, benchmark)")
    p_ai.add_argument("action", choices=["detect", "status", "setup", "config", "benchmark"])
    p_ai.add_argument("--model", default="", help="Model name")
    p_ai.add_argument("--prompt", default="Hello", help="Benchmark prompt")
    p_ai.add_argument("--backend", default="", choices=["", "ollama", "mlx"], help="AI backend (auto-detect if omitted)")
    p_ai.add_argument("--json", action="store_true", help="Output as JSON")
    p_ai.add_argument("key", nargs="?", help="Config key for set/unset")
    p_ai.add_argument("value", nargs="?", help="Config value for set")

    p_exec = sub.add_parser("exec", help="Execute natural language workspace command")
    p_exec.add_argument("query", help="Natural language query")
    p_exec.add_argument("--dry-run", action="store_true", help="Show intent without executing")

    args = parser.parse_args()

    if args.version:
        from importlib.metadata import version as v
        try:
            print(f"forge {v('forge-cli')}")
        except ImportError:
            print("forge 0.4.0")
        return

    if not args.command:
        parser.print_help()
        return

    cmds = {
        "init": cmd_init,
        "scan": cmd_scan,
        "status": cmd_status,
        "clone": cmd_clone,
        "health": cmd_health,
        "doctor": cmd_doctor,
        "feature": cmd_feature,
        "graph": cmd_graph,
        "install": cmd_install,
        "log": cmd_log,
        "pr": cmd_pr,
        "share": cmd_share,
        "notes": cmd_notes,
        "serve": cmd_serve,
        "config": cmd_config_path,
        "deps": cmd_deps,
        "cve": cmd_cve,
        "completion": cmd_completion,
        "ai": cmd_ai,
        "exec": cmd_exec,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
