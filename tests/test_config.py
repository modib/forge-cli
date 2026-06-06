import os


class TestDefaultConfig:
    def test_load_when_missing(self, ws_config):
        c = ws_config.load_config()
        assert c["version"] == 1
        assert c["repos"] == []
        assert c["groups"] == []
        assert c["features"] == []
        assert c["sessions"] == []

    def test_default_workspace_root(self, ws_config):
        c = ws_config.load_config()
        assert c["workspace_root"].endswith("Workspace")

    def test_default_providers(self, ws_config):
        c = ws_config.load_config()
        assert "github" in c["providers"]
        assert "gitlab" in c["providers"]


class TestLoadSave:
    def test_roundtrip(self, ws_config, tmp_workspace):
        ws_dir, _, _ = tmp_workspace
        c = ws_config.load_config()
        c["repos"].append({"name": "test", "path": "/tmp/test", "provider": "github"})
        ws_config.save_config(c)
        loaded = ws_config.load_config()
        assert len(loaded["repos"]) == 1
        assert loaded["repos"][0]["name"] == "test"

    def test_corrupt_json_falls_back_to_default(self, ws_config, tmp_workspace):
        ws_dir, _, _ = tmp_workspace
        config_path = ws_dir / "config.json"
        config_path.write_text("{bad json}")
        c = ws_config.load_config()
        assert c["version"] == 1

    def test_file_permissions_on_save(self, ws_config, tmp_workspace):
        ws_dir, _, _ = tmp_workspace
        c = ws_config.load_config()
        ws_config.save_config(c)
        config_path = ws_dir / "config.json"
        assert config_path.exists()
        mode = os.stat(config_path).st_mode & 0o777
        assert mode == 0o600


class TestRepoCRUD:
    def test_add_repo(self, ws_config):
        c = ws_config.load_config()
        repo = {"name": "my-repo", "path": "/tmp/my-repo", "provider": "github"}
        ws_config.add_repo(c, repo)
        assert len(c["repos"]) == 1

    def test_add_repo_updates_existing(self, ws_config):
        c = ws_config.load_config()
        ws_config.add_repo(c, {"name": "r", "path": "/tmp/r", "provider": "github"})
        ws_config.add_repo(c, {"name": "r", "path": "/tmp/r", "provider": "gitlab", "url": "https://gitlab.com/r"})
        assert len(c["repos"]) == 1
        assert c["repos"][0]["provider"] == "gitlab"

    def test_repo_by_name(self, ws_config):
        c = ws_config.load_config()
        ws_config.add_repo(c, {"name": "alpha", "path": "/tmp/alpha", "provider": "github"})
        found = ws_config.repo_by_name(c, "alpha")
        assert found is not None
        assert found["name"] == "alpha"

    def test_repo_by_name_missing(self, ws_config):
        c = ws_config.load_config()
        assert ws_config.repo_by_name(c, "nonexistent") is None

    def test_repo_by_path(self, ws_config):
        c = ws_config.load_config()
        ws_config.add_repo(c, {"name": "alpha", "path": "/tmp/alpha", "provider": "github"})
        found = ws_config.repo_by_path(c, "/tmp/alpha")
        assert found is not None

    def test_repo_by_path_normalizes(self, ws_config):
        c = ws_config.load_config()
        ws_config.add_repo(c, {"name": "alpha", "path": "/tmp/alpha", "provider": "github"})
        found = ws_config.repo_by_path(c, "/tmp/./alpha")
        assert found is not None

    def test_remove_repo(self, ws_config):
        c = ws_config.load_config()
        ws_config.add_repo(c, {"name": "r", "path": "/tmp/r", "provider": "github"})
        ws_config.remove_repo(c, "r")
        assert len(c["repos"]) == 0

    def test_remove_repo_nonexistent(self, ws_config):
        c = ws_config.load_config()
        ws_config.remove_repo(c, "phantom")
        assert len(c["repos"]) == 0


class TestFeatures:
    def test_add_feature(self, ws_config):
        c = ws_config.load_config()
        feature = {"id": "feat-001", "name": "dark-mode", "repos": ["repo-a"]}
        c["features"].append(feature)
        ws_config.save_config(c)
        loaded = ws_config.load_config()
        assert len(loaded["features"]) == 1
        assert loaded["features"][0]["name"] == "dark-mode"

    def test_feature_with_worktrees(self, ws_config):
        c = ws_config.load_config()
        feature = {"id": "feat-002", "name": "auth-rewrite", "repos": ["repo-a"], "worktrees": {"repo-a": "/tmp/wt/auth"}}
        c["features"].append(feature)
        ws_config.save_config(c)
        loaded = ws_config.load_config()
        assert loaded["features"][0]["worktrees"]["repo-a"] == "/tmp/wt/auth"


class TestNow:
    def test_now_iso_format(self, ws_config):
        ts = ws_config.now_iso()
        assert "T" in ts
        assert ts.endswith("+00:00") or "+00:" in ts or ts.endswith("Z")

    def test_now_not_empty(self, ws_config):
        assert ws_config.now_iso()
