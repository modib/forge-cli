from ws.git import sanitize_url, _detect_provider, run_git, is_git_repo


class TestSanitizeUrl:
    def test_https_clean(self):
        assert sanitize_url("https://github.com/user/repo.git") == "github.com/user/repo.git"

    def test_https_with_token(self):
        assert sanitize_url("https://token@github.com/user/repo.git") == "github.com/user/repo.git"

    def test_ssh_format(self):
        assert sanitize_url("git@github.com:user/repo.git") == "github.com/user/repo.git"

    def test_ssh_protocol(self):
        assert sanitize_url("ssh://git@github.com/user/repo") == "github.com/user/repo"

    def test_empty(self):
        assert sanitize_url("") == ""

    def test_none(self):
        assert sanitize_url(None) == ""

    def test_arbitrary_at(self):
        assert sanitize_url("user:pass@host.com/path") == "host.com/path"

    def test_no_credentials(self):
        assert sanitize_url("gitlab.com/org/project") == "gitlab.com/org/project"

    def test_git_suffix_stays(self):
        assert sanitize_url("https://github.com/user/repo.git").endswith(".git")


class TestDetectProvider:
    def test_github(self):
        assert _detect_provider("https://github.com/user/repo") == "github"

    def test_gitlab(self):
        assert _detect_provider("https://gitlab.com/user/repo") == "gitlab"

    def test_other(self):
        assert _detect_provider("https://bitbucket.org/user/repo") == "other"

    def test_empty(self):
        assert _detect_provider("") == "unknown"

    def test_none(self):
        assert _detect_provider(None) == "unknown"


class TestRunGit:
    def test_run_invalid_command(self):
        out, err, rc = run_git("/nonexistent", "status")
        assert rc != 0
        assert out == ""

    def test_run_invalid_path(self):
        out, err, rc = run_git("/tmp", "status")
        assert rc != 0
        assert out == ""


class TestIsGitRepo:
    def test_not_a_repo(self, tmp_path):
        assert is_git_repo(str(tmp_path)) is False

    def test_nonexistent_path(self):
        assert is_git_repo("/does/not/exist") is False
