import os
import subprocess
import pytest
from ws import graph as wsgraph


class TestCoChangeGraph:
    def test_nonexistent_path(self):
        result = wsgraph.co_change_graph("/nonexistent/path")
        assert "error" in result

    def test_not_git_repo(self, tmp_path):
        result = wsgraph.co_change_graph(str(tmp_path))
        assert "error" in result

    def test_empty_repo(self, tmp_git_repo):
        result = wsgraph.co_change_graph(str(tmp_git_repo))
        assert "nodes" in result
        assert "edges" in result

    def test_single_commit(self, tmp_git_repo):
        (tmp_git_repo / "file_a.txt").write_text("a")
        (tmp_git_repo / "file_b.txt").write_text("b")
        subprocess.run(["git", "add", "."], cwd=tmp_git_repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "add two files"], cwd=tmp_git_repo, capture_output=True, check=True)
        result = wsgraph.co_change_graph(str(tmp_git_repo), depth=10)
        assert len(result["nodes"]) >= 2
        assert any(n["id"] == "file_a.txt" for n in result["nodes"])
        assert any(n["id"] == "file_b.txt" for n in result["nodes"])
        assert any(e["source"] == "file_a.txt" and e["target"] == "file_b.txt" for e in result["edges"])

    def test_edge_weight(self, tmp_git_repo):
        (tmp_git_repo / "a.txt").write_text("a")
        (tmp_git_repo / "b.txt").write_text("b")
        subprocess.run(["git", "add", "."], cwd=tmp_git_repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "first"], cwd=tmp_git_repo, capture_output=True, check=True)
        (tmp_git_repo / "a.txt").write_text("a2")
        (tmp_git_repo / "b.txt").write_text("b2")
        subprocess.run(["git", "add", "."], cwd=tmp_git_repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "second"], cwd=tmp_git_repo, capture_output=True, check=True)
        result = wsgraph.co_change_graph(str(tmp_git_repo), depth=10)
        for e in result["edges"]:
            if e["source"] == "a.txt" and e["target"] == "b.txt":
                assert e["weight"] == 2
                break
        else:
            pytest.fail("Expected edge between a.txt and b.txt")


class TestBranchGraph:
    def test_nonexistent_path(self):
        result = wsgraph.branch_graph("/nonexistent")
        assert "error" in result

    def test_not_git(self, tmp_path):
        result = wsgraph.branch_graph(str(tmp_path))
        assert "error" in result

    def test_lists_branches(self, tmp_git_repo):
        result = wsgraph.branch_graph(str(tmp_git_repo))
        assert "branches" in result
        assert "current" in result
        assert result["current"] in result["branches"] or result["current"] == "detached"

    def test_with_feature_branch(self, tmp_git_repo):
        subprocess.run(["git", "checkout", "-b", "feature/test"], cwd=tmp_git_repo, capture_output=True, check=True)
        result = wsgraph.branch_graph(str(tmp_git_repo))
        assert "feature/test" in result["branches"]
        assert result["current"] == "feature/test"


class TestCrossRepoImpact:
    def test_empty(self):
        result = wsgraph.cross_repo_impact({})
        assert result == []

    def test_no_common_files(self, tmp_git_repo, tmp_path):
        repo_b = tmp_path / "repo-b"
        repo_b.mkdir()
        subprocess.run(["git", "init"], cwd=repo_b, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo_b, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=repo_b, capture_output=True, check=True)
        (repo_b / "unique.py").write_text("x")
        subprocess.run(["git", "add", "."], cwd=repo_b, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_b, capture_output=True, check=True)
        result = wsgraph.cross_repo_impact({"repo-a": str(tmp_git_repo), "repo-b": str(repo_b)})
        assert result == []

    def test_detects_common_files(self, tmp_git_repo, tmp_path):
        repo_b = tmp_path / "repo-b"
        repo_b.mkdir()
        subprocess.run(["git", "init"], cwd=repo_b, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo_b, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=repo_b, capture_output=True, check=True)
        (repo_b / "README.md").write_text("# Shared")
        (repo_b / "lib.py").write_text("shared lib")
        subprocess.run(["git", "add", "."], cwd=repo_b, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_b, capture_output=True, check=True)
        # tmp_git_repo already has README.md from conftest
        result = wsgraph.cross_repo_impact({"repo-a": str(tmp_git_repo), "repo-b": str(repo_b)})
        assert len(result) == 1
        assert set(result[0]["repo_a"]) == set(result[0]["repo_a"])  # order may vary
        assert "README.md" in result[0]["shared_files"]


class TestGenerateGraph:
    def test_repo_not_found(self, ws_config):
        result = wsgraph.generate_graph("no-such-repo")
        assert "error" in result
        assert "not found" in result["error"]

    def test_unknown_graph_type(self, ws_config, tmp_git_repo):
        import ws.config as cfg
        ws_root = tmp_git_repo.parent.parent / "Workspace"
        ws_root.mkdir(parents=True, exist_ok=True)
        c = ws_config.load_config()
        cfg.add_repo(c, {"name": "my-repo", "path": str(tmp_git_repo), "provider": "github", "url": "", "default_branch": "main"})
        cfg.save_config(c)
        result = wsgraph.generate_graph("my-repo", graph_type="invalid")
        assert "error" in result

    def test_co_change(self, ws_config, tmp_git_repo):
        import ws.config as cfg
        ws_root = tmp_git_repo.parent.parent / "Workspace"
        ws_root.mkdir(parents=True, exist_ok=True)
        c = ws_config.load_config()
        cfg.add_repo(c, {"name": "my-repo", "path": str(tmp_git_repo), "provider": "github", "url": "", "default_branch": "main"})
        cfg.save_config(c)
        result = wsgraph.generate_graph("my-repo", graph_type="co-change")
        assert "repo" in result
        assert result["repo"] == "my-repo"

    def test_branches(self, ws_config, tmp_git_repo):
        import ws.config as cfg
        ws_root = tmp_git_repo.parent.parent / "Workspace"
        ws_root.mkdir(parents=True, exist_ok=True)
        c = ws_config.load_config()
        cfg.add_repo(c, {"name": "my-repo", "path": str(tmp_git_repo), "provider": "github", "url": "", "default_branch": "main"})
        cfg.save_config(c)
        result = wsgraph.generate_graph("my-repo", graph_type="branches")
        assert "branches" in result
