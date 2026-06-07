import json
import subprocess
import pytest


@pytest.fixture
def tmp_forge_workspace(tmp_path):
    """Create a temporary workspace dir with a config.json."""
    forge_dir = tmp_path / ".forge"
    forge_dir.mkdir()
    workspace_root = tmp_path / "Workspace"
    workspace_root.mkdir()
    config = {
        "version": 1,
        "workspace_root": str(workspace_root),
        "providers": {"github": {"username": "test", "host": "github.com"}, "gitlab": {"username": "", "host": "gitlab.com"}},
        "repos": [],
        "groups": [],
        "features": [],
        "sessions": [],
    }
    config_path = forge_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2))
    return forge_dir, workspace_root, config


@pytest.fixture
def forge_config(monkeypatch, tmp_forge_workspace):
    """Patch config paths to point at tmp_forge_workspace, return the config module."""
    forge_dir, workspace_root, _ = tmp_forge_workspace
    import forge.config as cfg
    monkeypatch.setattr(cfg, "WORKSPACE_DIR", str(forge_dir))
    monkeypatch.setattr(cfg, "CONFIG_PATH", str(forge_dir / "config.json"))
    monkeypatch.setattr(cfg, "WORKSPACE_ROOT", str(workspace_root))
    return cfg


@pytest.fixture
def populated_config(forge_config):
    """Return a config module with 2 sample repos already loaded."""
    c = forge_config.load_config()
    forge_config.add_repo(c, {"name": "repo-a", "path": "/tmp/repo-a", "provider": "github", "url": "https://github.com/test/repo-a.git", "default_branch": "main"})
    forge_config.add_repo(c, {"name": "repo-b", "path": "/tmp/repo-b", "provider": "github", "url": "https://github.com/test/repo-b.git", "default_branch": "main"})
    forge_config.save_config(c)
    return forge_config


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