import os
import shutil
import subprocess
from . import config as cfg
from . import git


def scan_workspace():
    c = cfg.load_config()
    discovered = git.discover_repos(c.get("workspace_root", cfg.WORKSPACE_ROOT))
    added = []
    for repo in discovered:
        existing = cfg.repo_by_path(c, repo["path"])
        if not existing:
            cfg.add_repo(c, repo)
            added.append(repo["name"])
    cfg.save_config(c)
    return added, len(discovered)


def get_status(name=None):
    c = cfg.load_config()
    repos = c.get("repos", [])
    if name:
        repo = cfg.repo_by_name(c, name)
        repos = [repo] if repo else []
    results = []
    for r in repos:
        if not os.path.exists(r["path"]):
            results.append({**r, "exists": False, "error": "path not found"})
            continue
        if not git.is_git_repo(r["path"]):
            results.append({**r, "exists": True, "error": "not a git repo"})
            continue
        s = git.get_status(r["path"])
        results.append({**r, **s, "exists": True, "error": None})
    return results


def get_overall_status():
    c = cfg.load_config()
    results = get_status()
    total = len(results)
    dirty = sum(1 for r in results if r.get("dirty"))
    ahead = sum(1 for r in results if r.get("ahead", 0) > 0)
    behind = sum(1 for r in results if r.get("behind", 0) > 0)
    missing = sum(1 for r in results if not r.get("exists"))
    features = c.get("features", [])
    sessions = c.get("sessions", [])
    return {
        "total_repos": total,
        "dirty": dirty,
        "ahead": ahead,
        "behind": behind,
        "missing": missing,
        "active_features": len(features),
        "active_sessions": len(sessions),
        "repos": results,
    }


def health_check():
    checks = {}
    checks["brew"] = bool(shutil.which("brew"))
    checks["ollama"] = bool(shutil.which("ollama"))
    checks["gh"] = bool(shutil.which("gh"))
    checks["python3"] = bool(shutil.which("python3") or shutil.which("python"))
    checks["node"] = bool(shutil.which("node"))
    checks["npm"] = bool(shutil.which("npm"))
    if checks["gh"]:
        r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=10)
        checks["gh_auth"] = r.returncode == 0
    else:
        checks["gh_auth"] = False
    root = cfg.WORKSPACE_ROOT
    stat = shutil.disk_usage(root if os.path.exists(root) else "/")
    checks["disk_total_gb"] = round(stat.total / (1024**3), 1)
    checks["disk_free_gb"] = round(stat.free / (1024**3), 1)
    checks["disk_used_pct"] = round((stat.used / stat.total) * 100, 1)
    return checks


def init_workspace(provider=None):
    c = cfg.load_config()
    ensure_workspace_dir()
    if provider:
        if provider == "github":
            r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=10)
            if r.returncode != 0:
                print("Not authenticated with GitHub. Run: gh auth login")
        c["providers"]["github"]["username"] = _get_gh_user()
    cfg.save_config(c)
    return c


def ensure_workspace_dir():
    cfg.ensure_dir(cfg.WORKSPACE_DIR)
    cfg.ensure_dir(os.path.join(cfg.WORKSPACE_DIR, "sessions"))


def _get_gh_user():
    try:
        r = subprocess.run(["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except:
        return ""


def add_feature(name, repos=None):
    c = cfg.load_config()
    import uuid
    fid = f"feat-{uuid.uuid4().hex[:8]}"
    feature = {
        "id": fid,
        "name": name,
        "created": cfg.now_iso(),
        "repos": repos or [],
        "worktrees": {},
        "decisions": [],
    }
    c.setdefault("features", []).append(feature)
    cfg.save_config(c)
    return feature


def list_features():
    c = cfg.load_config()
    return c.get("features", [])
