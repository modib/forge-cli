import os
import subprocess


def run_git(path, *args):
    try:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return "", str(e), -1


def is_git_repo(path):
    stdout, _, rc = run_git(path, "rev-parse", "--git-dir")
    return rc == 0


def discover_repos(root):
    repos = []
    if not os.path.exists(root):
        return repos
    for entry in sorted(os.listdir(root)):
        full = os.path.join(root, entry)
        git_dir = os.path.join(full, ".git")
        if os.path.isdir(full) and os.path.isdir(git_dir):
            name = entry
            stdout, _, _ = run_git(full, "remote", "get-url", "origin")
            url = stdout if stdout else ""
            stdout, _, _ = run_git(full, "rev-parse", "--abbrev-ref", "HEAD")
            branch = stdout if stdout else "main"
            repos.append({
                "name": name,
                "path": full,
                "provider": _detect_provider(url),
                "url": url,
                "default_branch": branch,
            })
    return repos


def _detect_provider(url):
    if not url:
        return "unknown"
    if "github.com" in url:
        return "github"
    if "gitlab.com" in url:
        return "gitlab"
    return "other"


def sanitize_url(url):
    """Strip credentials from a remote URL for safe display."""
    if not url:
        return ""
    if url.startswith("https://"):
        rest = url[8:]
        if "@" in rest:
            rest = rest.split("@", 1)[1]
        return rest
    if url.startswith("git@"):
        rest = url[4:].replace(":", "/", 1)
        return rest
    if url.startswith("ssh://"):
        rest = url[6:]
        if "@" in rest:
            rest = rest.split("@", 1)[1]
        return rest
    if "@" in url:
        url = url.split("@", 1)[1]
    return url


def get_status(path):
    branch, _, _ = run_git(path, "rev-parse", "--abbrev-ref", "HEAD")
    stdout, _, _ = run_git(path, "status", "--porcelain")
    dirty = bool(stdout.strip())
    changed_files = len([line for line in stdout.split("\n") if line.strip()]) if stdout else 0

    stdout, _, _ = run_git(path, "remote")
    has_remote = bool(stdout.strip())
    remote_name = stdout.split("\n")[0].strip() if has_remote else ""

    remote_url = ""
    if has_remote:
        remote_url, _, _ = run_git(path, "remote", "get-url", remote_name)

    upstream_branch = ""
    has_upstream = False
    if branch != "HEAD":
        stdout, _, rc = run_git(path, "rev-parse", "--abbrev-ref", f"{branch}@{{u}}")
        if rc == 0 and stdout.strip():
            upstream_branch = stdout.strip()
            has_upstream = True

    ahead = behind = 0
    tracking = ""
    if has_upstream:
        tracking = upstream_branch
    elif has_remote and branch != "HEAD":
        tracking = f"{remote_name}/{branch}"
    if tracking:
        stdout, _, _ = run_git(path, "rev-list", "--left-right", "--count", f"HEAD...{tracking}")
        if stdout:
            parts = stdout.split()
            if len(parts) >= 2:
                ahead = int(parts[0])
                behind = int(parts[1])

    stdout, _, _ = run_git(path, "log", "-1", "--format=%H|%ai|%s")
    parts = stdout.split("|", 2) if stdout else ["", "", ""]
    last_commit_hash = parts[0] if len(parts) > 0 else ""
    last_commit_time = parts[1] if len(parts) > 1 else ""
    last_commit_msg = parts[2] if len(parts) > 2 else ""
    return {
        "branch": "detached" if branch == "HEAD" else (branch if branch else "detached"),
        "dirty": dirty,
        "changed_files": changed_files,
        "ahead": ahead,
        "behind": behind,
        "last_commit_hash": last_commit_hash,
        "last_commit_time": last_commit_time,
        "last_commit_msg": last_commit_msg,
        "has_remote": has_remote,
        "remote_name": remote_name,
        "remote_url": remote_url,
        "has_upstream": has_upstream,
        "upstream_branch": upstream_branch,
    }


def clone(url, target_dir, name=None):
    if name:
        target = os.path.join(target_dir, name)
    else:
        target = target_dir
    if os.path.exists(target):
        return f"already exists: {target}"
    result = subprocess.run(
        ["git", "clone", url, target],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        return f"error: {result.stderr.strip()}"
    return target
