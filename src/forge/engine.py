import json
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
    except Exception:
        return ""


def diagnose():
    c = cfg.load_config()
    issues = []
    for r in c.get("repos", []):
        if not os.path.exists(r["path"]):
            issues.append({"type": "missing_repo", "severity": "error", "repo": r["name"], "detail": f"Path not found: {r['path']}"})
            continue
        if not git.is_git_repo(r["path"]):
            issues.append({"type": "not_git", "severity": "error", "repo": r["name"], "detail": "Not a git repository"})
            continue
        s = git.get_status(r["path"])
        if not s.get("has_remote"):
            issues.append({"type": "no_remote", "severity": "warning", "repo": r["name"], "detail": "No git remote configured"})
        elif not s.get("has_upstream"):
            issues.append({"type": "no_upstream", "severity": "info", "repo": r["name"], "detail": f"Branch '{s['branch']}' has no upstream tracking"})

    for f in c.get("features", []):
        for repo_name, wt_path in f.get("worktrees", {}).items():
            if not os.path.exists(wt_path):
                issues.append({"type": "stale_worktree", "severity": "warning", "feature": f["name"], "repo": repo_name, "detail": f"Worktree path not found: {wt_path}"})

    h = health_check()
    if not h.get("brew"):
        issues.append({"type": "missing_tool", "severity": "warning", "detail": "Homebrew not installed"})
    if not h.get("ollama"):
        issues.append({"type": "missing_tool", "severity": "info", "detail": "Ollama not installed"})
    if h.get("disk_free_gb", 99) < 1:
        issues.append({"type": "low_disk", "severity": "error", "detail": f"Only {h['disk_free_gb']} GB disk free"})
    elif h.get("disk_free_gb", 99) < 5:
        issues.append({"type": "low_disk", "severity": "warning", "detail": f"Only {h['disk_free_gb']} GB disk free"})

    return {"total_issues": len(issues), "issues": issues}


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


def complete_feature(feature_id):
    c = cfg.load_config()
    feature = None
    for f in c.get("features", []):
        if f["id"] == feature_id or f["name"] == feature_id:
            feature = f
            break
    if not feature:
        return {"error": f"Feature not found: {feature_id}"}

    removed_worktrees = []
    failed_worktrees = []
    for repo_name, wt_path in feature.get("worktrees", {}).items():
        if os.path.exists(wt_path):
            r = subprocess.run(
                ["git", "worktree", "remove", wt_path],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0:
                removed_worktrees.append(repo_name)
            else:
                r2 = subprocess.run(
                    ["git", "worktree", "remove", "--force", wt_path],
                    capture_output=True, text=True, timeout=30,
                )
                if r2.returncode == 0:
                    removed_worktrees.append(repo_name)
                else:
                    failed_worktrees.append(repo_name)

    feature_id_val = feature["id"]
    c["features"] = [f for f in c["features"] if f["id"] != feature_id_val]
    cfg.save_config(c)

    return {
        "id": feature_id_val,
        "name": feature["name"],
        "removed_worktrees": removed_worktrees,
        "failed_worktrees": failed_worktrees,
    }


def create_prs(feature_id, title=None, body=None, draft=False):
    c = cfg.load_config()
    feature = None
    for f in c.get("features", []):
        if f["id"] == feature_id or f["name"] == feature_id:
            feature = f
            break
    if not feature:
        return {"error": f"Feature not found: {feature_id}"}
    if not feature.get("repos"):
        return {"error": f"No repos in feature '{feature['name']}'"}
    if not shutil.which("gh"):
        return {"error": "GitHub CLI (gh) not found. Install with: brew install gh"}

    pr_title = title or f"Feature: {feature['name']}"
    base_body = body or f"Automated PR for feature **{feature['name']}** ({feature['id']})."
    prs = []

    for repo_name in feature["repos"]:
        repo = cfg.repo_by_name(c, repo_name)
        if not repo:
            prs.append({"repo": repo_name, "error": "Repo not found in workspace config"})
            continue
        if not os.path.exists(repo["path"]):
            prs.append({"repo": repo_name, "error": "Repo path not found"})
            continue
        branch = f"feature/{feature['name']}"
        r = subprocess.run(
            ["git", "rev-parse", "--verify", branch],
            cwd=repo["path"], capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            prs.append({"repo": repo_name, "error": f"Branch '{branch}' not found"})
            continue
        repo_url = repo.get("url", "")
        cmd = ["gh", "pr", "create", "--repo", repo_url, "--head", branch, "--title", pr_title, "--body", base_body]
        if draft:
            cmd.append("--draft")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                url = r.stdout.strip()
                prs.append({"repo": repo_name, "url": url, "status": "created"})
            else:
                prs.append({"repo": repo_name, "error": r.stderr.strip() or r.stdout.strip()})
        except subprocess.TimeoutExpired:
            prs.append({"repo": repo_name, "error": "Timed out creating PR"})

    created = [p for p in prs if p.get("status") == "created"]
    if len(created) > 1:
        for p in created:
            refs = [f"- {other['repo']}: {other['url']}" for other in created if other["repo"] != p["repo"]]
            if not refs:
                continue
            cross_ref_body = base_body + "\n\n## Related PRs\n" + "\n".join(refs)
            repo = cfg.repo_by_name(c, p["repo"])
            if not repo:
                continue
            try:
                pr_number = p["url"].rstrip("/").split("/")[-1]
                subprocess.run(
                    ["gh", "pr", "edit", pr_number, "--repo", repo.get("url", ""), "--body", cross_ref_body],
                    capture_output=True, text=True, timeout=15,
                )
                p["cross_referenced"] = True
            except subprocess.TimeoutExpired:
                pass

    return {"feature": feature["name"], "id": feature["id"], "prs": prs}


def list_sessions(limit=10):
    c = cfg.load_config()
    sessions = c.get("sessions", [])
    result = []
    for s in reversed(sessions):
        result.append({
            "id": s.get("id"),
            "agent": s.get("agent"),
            "feature": s.get("feature", ""),
            "started": s.get("started", ""),
            "context_preview": s.get("context", "")[:80] if s.get("context") else "",
        })
        if len(result) >= limit:
            break
    return result


def get_session(session_id):
    meta_path = os.path.join(cfg.WORKSPACE_DIR, "sessions", session_id, "meta.json")
    transcript_path = os.path.join(cfg.WORKSPACE_DIR, "sessions", session_id, "transcript.md")
    session = None
    if os.path.exists(meta_path):
        import json
        with open(meta_path) as f:
            session = json.load(f)
    if not session:
        c = cfg.load_config()
        for s in c.get("sessions", []):
            if s["id"] == session_id:
                session = s
                break
    if not session:
        return {"error": f"Session not found: {session_id}"}
    transcript = ""
    if os.path.exists(transcript_path):
        with open(transcript_path) as f:
            transcript = f.read()
    return {"session": session, "transcript": transcript}


def agent_handoff(session_id, target_agent):
    c = cfg.load_config()
    session = None
    for s in c.get("sessions", []):
        if s["id"] == session_id:
            session = s
            break
    if not session:
        session_dir = os.path.join(cfg.WORKSPACE_DIR, "sessions", session_id)
        meta_path = os.path.join(session_dir, "meta.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                session = json.load(f)
    if not session:
        return {"error": f"Session not found: {session_id}"}
    session_data = get_session(session_id)
    if "error" in session_data:
        return session_data
    transcript = session_data.get("transcript", "")
    decisions = []
    feature_info = None
    if session.get("feature"):
        for f in c.get("features", []):
            if f["id"] == session["feature"] or f["name"] == session["feature"]:
                feature_info = f
                decisions = f.get("decisions", [])
                break
    workspace_status = get_overall_status()
    handoff = {
        "handoff_from": "forge",
        "handoff_to": target_agent,
        "session_id": session_id,
        "agent": session.get("agent", "unknown"),
        "started": session.get("started", "unknown"),
        "context": session.get("context", ""),
        "feature": feature_info,
        "decisions": decisions,
        "workspace_status": {
            "total_repos": workspace_status["total_repos"],
            "dirty": workspace_status["dirty"],
            "ahead": workspace_status["ahead"],
            "behind": workspace_status["behind"],
        },
        "transcript_excerpt": transcript[-3000:] if len(transcript) > 3000 else transcript,
        "transcript_length": len(transcript),
    }
    handoffs_dir = os.path.join(cfg.WORKSPACE_DIR, "handoffs")
    os.makedirs(handoffs_dir, exist_ok=True)
    handoff_file = os.path.join(handoffs_dir, f"{session_id}-to-{target_agent}.json")
    with open(handoff_file, "w") as f:
        json.dump(handoff, f, indent=2)
    handoff_md = os.path.join(handoffs_dir, f"{session_id}-to-{target_agent}.md")
    lines = [f"# Agent Handoff: {session_id}", ""]
    lines.append(f"**From:** {session.get('agent', 'unknown')} → **To:** {target_agent}")
    lines.append(f"**Started:** {session.get('started', 'unknown')}")
    if session.get("context"):
        lines.append("")
        lines.append("## Original Context")
        lines.append(session["context"])
    if feature_info:
        lines.append("")
        lines.append(f"## Feature: {feature_info.get('name', '?')} ({feature_info.get('id', '?')})")
        if feature_info.get("repos"):
            lines.append(f"**Repos:** {', '.join(feature_info['repos'])}")
        if feature_info.get("worktrees"):
            lines.append("**Worktrees:**")
            for repo, path in feature_info["worktrees"].items():
                lines.append(f"- {repo}: {path}")
    if decisions:
        lines.append("")
        lines.append("## Decisions")
        for d in decisions:
            ts = d.get("timestamp", "").split(".")[0].replace("T", " ")
            author = d.get("author", "?")
            msg = d.get("message", "")
            dtype = d.get("type", "info")
            lines.append(f"- [{dtype}] {ts} ({author}): {msg}")
    if transcript:
        lines.append("")
        lines.append("## Recent Transcript")
        excerpt = transcript[-2000:] if len(transcript) > 2000 else transcript
        lines.append(excerpt)
    lines.append("")
    lines.append("---")
    lines.append("_Generated by Forge Agent Handoff_")
    with open(handoff_md, "w") as f:
        f.write("\n".join(lines))
    return {
        "session_id": session_id,
        "handoff_to": target_agent,
        "handoff_json": handoff_file,
        "handoff_md": handoff_md,
        "transcript_length": len(transcript),
        "decisions_count": len(decisions),
    }


def search_sessions(query, limit=10):
    c = cfg.load_config()
    q = query.lower()
    results = []
    for s in reversed(c.get("sessions", [])):
        if len(results) >= limit:
            break
        sid = s.get("id", "")
        if q in sid.lower():
            results.append({"session": s, "match_field": "id", "excerpt": sid})
            continue
        agent = s.get("agent", "")
        if q in agent.lower():
            results.append({"session": s, "match_field": "agent", "excerpt": agent})
            continue
        context = s.get("context", "")
        if q in context.lower():
            excerpt = context[:200]
            idx = context.lower().find(q)
            if idx > 0:
                excerpt = context[max(0, idx - 40):idx + 200]
            results.append({"session": s, "match_field": "context", "excerpt": excerpt})
            continue
        feat = s.get("feature", "")
        if feat:
            matched = False
            for f in c.get("features", []):
                if (f["id"] == feat or f["name"] == feat) and q in f["name"].lower():
                    results.append({"session": s, "match_field": "feature", "excerpt": f["name"]})
                    matched = True
                    break
            if matched:
                continue
        transcript_path = os.path.join(cfg.WORKSPACE_DIR, "sessions", sid, "transcript.md")
        if os.path.exists(transcript_path):
            try:
                with open(transcript_path) as f:
                    content = f.read()
                if q in content.lower():
                    idx = content.lower().find(q)
                    excerpt = content[max(0, idx - 60):idx + 200]
                    results.append({"session": s, "match_field": "transcript", "excerpt": excerpt})
            except OSError:
                pass
    return results


def diff_sessions(session_id_a, session_id_b):
    a_data = get_session(session_id_a)
    b_data = get_session(session_id_b)
    if "error" in a_data:
        return {"error": a_data["error"]}
    if "error" in b_data:
        return {"error": b_data["error"]}
    a = a_data["session"]
    b = b_data["session"]
    a_transcript = a_data.get("transcript", "")
    b_transcript = b_data.get("transcript", "")
    import difflib
    transcript_diff = list(difflib.unified_diff(
        a_transcript.splitlines(keepends=True),
        b_transcript.splitlines(keepends=True),
        fromfile=f"session/{session_id_a}",
        tofile=f"session/{session_id_b}",
        lineterm="",
    ))
    return {
        "session_a": session_id_a,
        "session_b": session_id_b,
        "agent": {"a": a.get("agent", ""), "b": b.get("agent", "")},
        "started": {"a": a.get("started", ""), "b": b.get("started", "")},
        "context": {"a": a.get("context", ""), "b": b.get("context", "")},
        "feature": {"a": a.get("feature", ""), "b": b.get("feature", "")},
        "transcript_length": {"a": len(a_transcript), "b": len(b_transcript)},
        "transcript_diff_lines": len(transcript_diff),
        "transcript_diff": transcript_diff[:100],
    }


def validate_config(fix=False):
    c = cfg.load_config()
    issues = []
    path = cfg.CONFIG_PATH
    if not os.path.exists(path):
        return {"valid": False, "issues": [{"severity": "error", "detail": f"Config file not found: {path}"}]}
    if not isinstance(c, dict):
        issues.append({"severity": "error", "detail": "Config is not a valid JSON object"})
        return {"valid": False, "issues": issues}
    if c.get("version") != 1:
        issues.append({"severity": "warning", "detail": f"Unknown config version: {c.get('version')}"})
    ws_root = c.get("workspace_root", "")
    if not ws_root:
        issues.append({"severity": "error", "detail": "Missing workspace_root"})
    elif not os.path.exists(ws_root):
        issues.append({"severity": "warning", "detail": f"Workspace root does not exist: {ws_root}"})
    names = set()
    paths = set()
    for r in c.get("repos", []):
        name = r.get("name", "")
        rpath = r.get("path", "")
        if not name:
            issues.append({"severity": "error", "repo": "(unnamed)", "detail": "Repo entry missing name"})
            continue
        if name in names:
            issues.append({"severity": "error", "repo": name, "detail": "Duplicate repo name"})
        names.add(name)
        norm_path = os.path.normpath(rpath) if rpath else ""
        if norm_path in paths:
            issues.append({"severity": "error", "repo": name, "detail": "Duplicate repo path"})
        paths.add(norm_path)
        if not rpath:
            issues.append({"severity": "error", "repo": name, "detail": "Missing path"})
        elif not os.path.exists(rpath):
            issues.append({"severity": "warning", "repo": name, "detail": f"Path not found: {rpath}"})
    for f in c.get("features", []):
        fid = f.get("id", f.get("name", "(unnamed)"))
        for repo_name in f.get("repos", []):
            if not cfg.repo_by_name(c, repo_name):
                issues.append({"severity": "warning", "feature": f.get("name", fid), "detail": f"References missing repo: {repo_name}"})
        for repo_name, wt_path in f.get("worktrees", {}).items():
            if not os.path.exists(wt_path):
                issues.append({"severity": "warning", "feature": f.get("name", fid), "detail": f"Stale worktree: {repo_name} -> {wt_path}"})
    if fix:
        repaired = []
        for r in list(c.get("repos", [])):
            if not os.path.exists(r["path"]):
                cfg.remove_repo(c, r["name"])
                repaired.append(f"Removed stale repo: {r['name']} (path not found)")
        for f in c.get("features", []):
            for repo_name in list(f.get("worktrees", {}).keys()):
                wt_path = f["worktrees"][repo_name]
                if not os.path.exists(wt_path):
                    del f["worktrees"][repo_name]
                    repaired.append(f"Removed stale worktree: {f.get('name')}/{repo_name}")
        if repaired:
            cfg.save_config(c)
        issues = [i for i in issues if "Stale worktree" not in i.get("detail", "")]
        issues = [i for i in issues if "Path not found" not in i.get("detail", "")]
    result = {"valid": len([i for i in issues if i["severity"] == "error"]) == 0, "issues": issues}
    if fix and repaired:
        result["_repaired"] = repaired
    return result
