import os
import json
import pytest
from ws import engine


class TestInitWorkspace:
    def test_init_creates_dir(self, ws_config, tmp_workspace):
        ws_dir, ws_root, _ = tmp_workspace
        c = engine.init_workspace()
        assert os.path.exists(str(ws_dir))
        sessions_dir = os.path.join(str(ws_dir), "sessions")
        assert os.path.exists(sessions_dir)


class TestScan:
    def test_scan_empty(self, ws_config, tmp_workspace):
        _, ws_root, _ = tmp_workspace
        added, total = engine.scan_workspace()
        assert added == []
        assert total == 0

    def test_scan_discovers_repo(self, ws_config, tmp_git_repo, tmp_workspace):
        _, ws_root, _ = tmp_workspace
        import ws.config as cfg
        import shutil
        shutil.move(str(tmp_git_repo), str(ws_root / tmp_git_repo.name))
        added, total = engine.scan_workspace()
        assert total == 1
        assert tmp_git_repo.name in added


class TestStatus:
    def test_get_status_empty(self, ws_config):
        results = engine.get_status()
        assert results == []

    def test_get_status_missing_path(self, ws_config, populated_config):
        results = engine.get_status()
        assert len(results) == 2
        for r in results:
            assert r.get("exists") is False
            assert r.get("error") == "path not found"

    def test_get_overall_status(self, ws_config, populated_config):
        s = engine.get_overall_status()
        assert s["total_repos"] == 2
        assert s["missing"] == 2
        assert "repos" in s

    def test_get_status_by_name(self, ws_config, populated_config):
        results = engine.get_status("repo-a")
        assert len(results) == 1
        assert results[0]["name"] == "repo-a"


class TestHealth:
    def test_health_returns_checks(self):
        h = engine.health_check()
        assert "brew" in h
        assert "ollama" in h
        assert "gh" in h
        assert "python3" in h
        assert "disk_total_gb" in h
        assert "disk_free_gb" in h
        assert "disk_used_pct" in h

    def test_health_python_found(self):
        h = engine.health_check()
        assert h["python3"] is True

    def test_health_disk_reasonable(self):
        h = engine.health_check()
        assert h["disk_total_gb"] > 0
        assert h["disk_free_gb"] >= 0
        assert 0 <= h["disk_used_pct"] <= 100


class TestFeatures:
    def test_add_feature(self, ws_config):
        feat = engine.add_feature("dark-mode", repos=["repo-a", "repo-b"])
        assert feat["name"] == "dark-mode"
        assert feat["repos"] == ["repo-a", "repo-b"]
        assert feat["id"].startswith("feat-")

    def test_list_features(self, ws_config):
        engine.add_feature("f1")
        engine.add_feature("f2")
        features = engine.list_features()
        assert len(features) == 2
        names = [f["name"] for f in features]
        assert "f1" in names
        assert "f2" in names

    def test_add_feature_saves_to_config(self, ws_config):
        feat = engine.add_feature("persist-test")
        c = ws_config.load_config()
        assert any(f["id"] == feat["id"] for f in c["features"])

    def test_complete_feature_by_id(self, ws_config):
        feat = engine.add_feature("complete-me")
        result = engine.complete_feature(feat["id"])
        assert "error" not in result
        assert result["name"] == "complete-me"
        c = ws_config.load_config()
        assert all(f["id"] != feat["id"] for f in c["features"])

    def test_complete_feature_by_name(self, ws_config):
        engine.add_feature("by-name")
        result = engine.complete_feature("by-name")
        assert "error" not in result
        c = ws_config.load_config()
        assert all(f["name"] != "by-name" for f in c["features"])

    def test_complete_nonexistent(self, ws_config):
        result = engine.complete_feature("nonexistent-feature")
        assert "error" in result

    def test_complete_with_worktree(self, ws_config):
        feat = engine.add_feature("with-wt")
        feat_id = feat["id"]
        c = ws_config.load_config()
        for f in c["features"]:
            if f["id"] == feat_id:
                f["worktrees"]["repo-a"] = "/nonexistent/worktree"
        ws_config.save_config(c)
        result = engine.complete_feature(feat_id)
        assert "error" not in result


class TestDiagnose:
    def test_healthy_empty(self, ws_config):
        d = engine.diagnose()
        assert d["total_issues"] >= 0

    def test_detects_missing_repo(self, ws_config, populated_config):
        d = engine.diagnose()
        types = [i["type"] for i in d["issues"]]
        assert "missing_repo" in types

    def test_detects_no_remote(self, ws_config, populated_config, tmp_git_repo):
        import shutil
        from ws import config as cfg
        ws_root = tmp_git_repo.parent.parent / "Workspace"
        ws_root.mkdir(parents=True, exist_ok=True)
        dest = ws_root / "noremote"
        shutil.copytree(str(tmp_git_repo), str(dest))
        c = ws_config.load_config()
        ws_config.add_repo(c, {"name": "noremote", "path": str(dest), "provider": "unknown", "url": "", "default_branch": "main"})
        ws_config.save_config(c)
        d = engine.diagnose()
        types = [i["type"] for i in d["issues"]]
        assert "no_remote" in types

    def test_detects_stale_worktree(self, ws_config):
        c = ws_config.load_config()
        ws_config.add_repo(c, {"name": "repo", "path": "/tmp/repo", "provider": "github", "url": "", "default_branch": "main"})
        c.setdefault("features", []).append({"id": "feat-1", "name": "stale", "worktrees": {"repo": "/nonexistent/wt"}})
        ws_config.save_config(c)
        d = engine.diagnose()
        types = [i["type"] for i in d["issues"]]
        assert "stale_worktree" in types
