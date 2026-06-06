import json
import os
import subprocess
import pytest


@pytest.fixture
def tmp_workspace(tmp_path):
    """Create a temporary workspace dir with a config.json."""
    ws_dir = tmp_path / ".workspace"
    ws_dir.mkdir()
    ws_root = tmp_path / "Workspace"
    ws_root.mkdir()
    config = {
        "version": 1,
        "workspace_root": str(ws_root),
        "providers": {"github": {"username": "test", "host": "github.com"}, "gitlab": {"username": "", "host": "gitlab.com"}},
        "repos": [],
        "groups": [],
        "features": [],
        "sessions": [],
    }
    config_path = ws_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2))
    return ws_dir, ws_root, config


@pytest.fixture
def ws_config(monkeypatch, tmp_workspace):
    """Patch config paths to point at tmp_workspace, return the config module."""
    ws_dir, ws_root, _ = tmp_workspace
    import ws.config as cfg
    monkeypatch.setattr(cfg, "WORKSPACE_DIR", str(ws_dir))
    monkeypatch.setattr(cfg, "CONFIG_PATH", str(ws_dir / "config.json"))
    monkeypatch.setattr(cfg, "WORKSPACE_ROOT", str(ws_root))
    return cfg


@pytest.fixture
def populated_config(ws_config):
    """Return a config module with 2 sample repos already loaded."""
    c = ws_config.load_config()
    ws_config.add_repo(c, {"name": "repo-a", "path": "/tmp/repo-a", "provider": "github", "url": "https://github.com/test/repo-a.git", "default_branch": "main"})
    ws_config.add_repo(c, {"name": "repo-b", "path": "/tmp/repo-b", "provider": "github", "url": "https://github.com/test/repo-b.git", "default_branch": "main"})
    ws_config.save_config(c)
    return ws_config


@pytest.fixture
def tmp_git_repo(tmp_path):
    """Create a real git repository at tmp_path/repo with an initial commit."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, capture_output=True, check=True)
    readme = repo_dir / "README.md"
    readme.write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=repo_dir, capture_output=True, check=True)
    return repo_dir


@pytest.fixture
def captured_print(monkeypatch):
    """Capture print() calls into a list for assertion."""
    out = []
    monkeypatch.setattr("builtins.print", lambda *a, **kw: out.append(" ".join(str(x) for x in a)))
    return out