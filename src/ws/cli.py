import argparse
import os
import subprocess
import sys
from . import config as cfg
from . import engine
from . import git


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
        last = r.get("last_commit_msg", "")
        if len(last) > 50:
            last = last[:47] + "..."
        print(f"  {name}{dirty_mark}  \033[36m{branch}\033[0m{ahead_behind}")
        if last:
            print(f"    {last}")

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
        print(f"  Use: ws feature worktree {feat['id']} <repo>")
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
        ws_dir = os.path.join(cfg.WORKSPACE_DIR, "..", ".workspaces", fname)
        os.makedirs(ws_dir, exist_ok=True)
        branch = f"feature/{fname}"
        result = subprocess.run(
            ["git", "worktree", "add", "-b", branch, os.path.join(ws_dir, repo_name), "HEAD"],
            cwd=repo["path"], capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"Worktree error: {result.stderr.strip() or result.stdout.strip()}")
            return
        feature.setdefault("worktrees", {})[repo_name] = os.path.join(ws_dir, repo_name)
        cfg.save_config(c)
        print(f"Created worktree for {repo_name} at {os.path.join(ws_dir, repo_name)}")
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


def cmd_serve(args):
    import asyncio
    from .server import run_server
    asyncio.run(run_server())


def cmd_config_path(args):
    print(cfg.CONFIG_PATH)


def main():
    parser = argparse.ArgumentParser(prog="ws", description="Brewix Workspace CLI")
    parser.add_argument("--version", action="store_true", help="Show version")

    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Initialize workspace config")
    p_init.add_argument("--provider", choices=["github", "gitlab"], help="Auth provider")

    p_scan = sub.add_parser("scan", help="Discover repos in workspace root")

    p_status = sub.add_parser("status", help="Show workspace status")
    p_status.add_argument("name", nargs="?", help="Show status for a specific repo")
    p_status.add_argument("--json", action="store_true", help="Output as JSON")

    p_clone = sub.add_parser("clone", help="Clone a repo into workspace")
    p_clone.add_argument("url", help="Repository URL")
    p_clone.add_argument("--name", "-n", help="Override repo name")

    p_health = sub.add_parser("health", help="Check dev environment health")

    p_feat = sub.add_parser("feature", help="Manage features")
    p_feat.add_argument("action", choices=["create", "list", "worktree"], help="Feature action")
    p_feat.add_argument("name", nargs="?", help="Feature name")
    p_feat.add_argument("--repos", "-r", help="Comma-separated repo names")
    p_feat.add_argument("--repo", help="Repo name for worktree command")

    p_share = sub.add_parser("share", help="Share a note across projects")
    p_share.add_argument("content", help="Note content")
    p_share.add_argument("--group", "-g", default="default", help="Group name")
    p_share.add_argument("--label", "-l", help="Optional label")

    p_notes = sub.add_parser("notes", help="List shared notes")
    p_notes.add_argument("group", nargs="?", default="default", help="Group name")

    p_serve = sub.add_parser("serve", help="Start MCP server (stdio)")

    p_config = sub.add_parser("config", help="Show config path")
    p_config.add_argument("sub", nargs="?", default="path", choices=["path"])

    args = parser.parse_args()

    if args.version:
        from importlib.metadata import version as v
        try:
            print(f"ws {v('ws-cli')}")
        except:
            print("ws 0.1.0")
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
        "feature": cmd_feature,
        "share": cmd_share,
        "notes": cmd_notes,
        "serve": cmd_serve,
        "config": cmd_config_path,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
