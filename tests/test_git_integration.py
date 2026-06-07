import subprocess
from forge.git import is_git_repo, get_status, discover_repos, run_git


class TestIsGitRepoIntegration:
    def test_is_git_repo(self, tmp_git_repo):
        assert is_git_repo(str(tmp_git_repo)) is True


class TestGetStatus:
    def test_basic_status(self, tmp_git_repo):
        s = get_status(str(tmp_git_repo))
        assert s["branch"] == "master" or s["branch"] == "main"
        assert s["dirty"] is False
        assert s["changed_files"] == 0
        assert s["ahead"] == 0
        assert s["behind"] == 0
        assert s["last_commit_msg"] == "initial commit"

    def test_dirty_repo(self, tmp_git_repo):
        (tmp_git_repo / "newfile.txt").write_text("dirty")
        s = get_status(str(tmp_git_repo))
        assert s["dirty"] is True
        assert s["changed_files"] >= 1

    def test_detached_head(self, tmp_git_repo):
        subprocess.run(["git", "checkout", "--detach", "HEAD"], cwd=tmp_git_repo, capture_output=True, check=True)
        s = get_status(str(tmp_git_repo))
        assert s["branch"] == "detached"

    def test_no_remote(self, tmp_git_repo):
        s = get_status(str(tmp_git_repo))
        assert s["has_remote"] is False
        assert s["remote_url"] == ""
        assert s["has_upstream"] is False

    def test_with_remote(self, tmp_git_repo):
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/test/repo.git"], cwd=tmp_git_repo, capture_output=True, check=True)
        s = get_status(str(tmp_git_repo))
        assert s["has_remote"] is True
        assert s["remote_name"] == "origin"
        assert "github.com/test/repo" in s["remote_url"]
        assert s["has_upstream"] is False


class TestDiscoverRepos:
    def test_empty_root(self, tmp_path):
        repos = discover_repos(str(tmp_path))
        assert repos == []

    def test_nonexistent_root(self):
        repos = discover_repos("/does/not/exist")
        assert repos == []

    def test_discovers_repo(self, tmp_git_repo):
        parent = tmp_git_repo.parent
        repos = discover_repos(str(parent))
        names = [r["name"] for r in repos]
        assert "repo" in names

    def test_discovers_only_git_dirs(self, tmp_path):
        (tmp_path / "plain_dir").mkdir()
        (tmp_path / "plain_file.txt").write_text("hello")
        repos = discover_repos(str(tmp_path))
        assert repos == []


class TestRunGitIntegration:
    def test_success(self, tmp_git_repo):
        out, err, rc = run_git(str(tmp_git_repo), "rev-parse", "--abbrev-ref", "HEAD")
        assert rc == 0
        assert out in ("master", "main")

    def test_failure(self, tmp_path):
        out, err, rc = run_git(str(tmp_path), "status")
        assert rc != 0

    def test_timeout_fake(self, monkeypatch):
        def fake_run(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="git", timeout=0.001)
        monkeypatch.setattr(subprocess, "run", fake_run)
        out, err, rc = run_git("/tmp", "status")
        assert rc == -1
