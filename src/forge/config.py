import json
import os
from datetime import datetime, timezone

# Primary: ~/.forge/. Fallback: ~/.workspace/ for backward compat.
_FORGE_DIR = os.path.expanduser(os.environ.get("FORGE_CONFIG_DIR", os.environ.get("WS_CONFIG_DIR", "~/.forge")))
_FORGE_LEGACY_FALLBACK = os.path.expanduser("~/.workspace")
WORKSPACE_DIR = _FORGE_DIR if os.path.exists(_FORGE_DIR) or not os.path.exists(_FORGE_LEGACY_FALLBACK) else _FORGE_LEGACY_FALLBACK
CONFIG_PATH = os.path.join(WORKSPACE_DIR, "config.json")
WORKSPACE_ROOT = os.path.expanduser(os.environ.get("FORGE_WORKSPACE_ROOT", os.environ.get("WS_WORKSPACE_ROOT", "~/Workspace")))


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def default_config():
    return {
        "version": 1,
        "workspace_root": WORKSPACE_ROOT,
        "providers": {
            "github": {"username": "", "host": "github.com"},
            "gitlab": {"username": "", "host": "gitlab.com"},
        },
        "repos": [],
        "groups": [],
        "features": [],
        "sessions": [],
    }


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return default_config()
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default_config()


def save_config(config):
    ensure_dir(WORKSPACE_DIR)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2, default=str)
    os.chmod(CONFIG_PATH, 0o600)


def repo_by_path(config, path):
    norm = os.path.normpath(path)
    for r in config.get("repos", []):
        if os.path.normpath(r["path"]) == norm:
            return r
    return None


def repo_by_name(config, name):
    for r in config.get("repos", []):
        if r["name"] == name:
            return r
    return None


def add_repo(config, repo):
    existing = repo_by_path(config, repo["path"])
    if existing:
        existing.update(repo)
        return existing
    config["repos"].append(repo)
    return repo


def remove_repo(config, name):
    config["repos"] = [r for r in config["repos"] if r["name"] != name]


def now_iso():
    return datetime.now(timezone.utc).isoformat()
