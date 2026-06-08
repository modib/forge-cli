import os
import subprocess
from forge import engine


class TestInitWorkspace:
    def test_init_creates_dir(self, forge_config, tmp_forge_workspace):
        forge_dir, workspace_root, _ = tmp_forge_workspace
        engine.init_workspace()
        assert os.path.exists(str(forge_dir))
        sessions_dir = os.path.join(str(forge_dir), "sessions")
        assert os.path.exists(sessions_dir)


class TestScan:
    def test_scan_empty(self, forge_config, tmp_forge_workspace):
        _, workspace_root, _ = tmp_forge_workspace
        added, total = engine.scan_workspace()
        assert added == []
        assert total == 0

    def test_scan_discovers_repo(self, forge_config, tmp_git_repo, tmp_forge_workspace):
        _, workspace_root, _ = tmp_forge_workspace
        import shutil
        shutil.move(str(tmp_git_repo), str(workspace_root / tmp_git_repo.name))
        added, total = engine.scan_workspace()
        assert total == 1
        assert tmp_git_repo.name in added


class TestStatus:
    def test_get_status_empty(self, forge_config):
        results = engine.get_status()
        assert results == []

    def test_get_status_missing_path(self, forge_config, populated_config):
        results = engine.get_status()
        assert len(results) == 2
        for r in results:
            assert r.get("exists") is False
            assert r.get("error") == "path not found"

    def test_get_overall_status(self, forge_config, populated_config):
        s = engine.get_overall_status()
        assert s["total_repos"] == 2
        assert s["missing"] == 2
        assert "repos" in s

    def test_get_status_by_name(self, forge_config, populated_config):
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
    def test_add_feature(self, forge_config):
        feat = engine.add_feature("dark-mode", repos=["repo-a", "repo-b"])
        assert feat["name"] == "dark-mode"
        assert feat["repos"] == ["repo-a", "repo-b"]
        assert feat["id"].startswith("feat-")

    def test_list_features(self, forge_config):
        engine.add_feature("f1")
        engine.add_feature("f2")
        features = engine.list_features()
        assert len(features) == 2
        names = [f["name"] for f in features]
        assert "f1" in names
        assert "f2" in names

    def test_add_feature_saves_to_config(self, forge_config):
        feat = engine.add_feature("persist-test")
        c = forge_config.load_config()
        assert any(f["id"] == feat["id"] for f in c["features"])

    def test_complete_feature_by_id(self, forge_config):
        feat = engine.add_feature("complete-me")
        result = engine.complete_feature(feat["id"])
        assert "error" not in result
        assert result["name"] == "complete-me"
        c = forge_config.load_config()
        assert all(f["id"] != feat["id"] for f in c["features"])

    def test_complete_feature_by_name(self, forge_config):
        engine.add_feature("by-name")
        result = engine.complete_feature("by-name")
        assert "error" not in result
        c = forge_config.load_config()
        assert all(f["name"] != "by-name" for f in c["features"])

    def test_complete_nonexistent(self, forge_config):
        result = engine.complete_feature("nonexistent-feature")
        assert "error" in result

    def test_complete_with_worktree(self, forge_config):
        feat = engine.add_feature("with-wt")
        feat_id = feat["id"]
        c = forge_config.load_config()
        for f in c["features"]:
            if f["id"] == feat_id:
                f["worktrees"]["repo-a"] = "/nonexistent/worktree"
        forge_config.save_config(c)
        result = engine.complete_feature(feat_id)
        assert "error" not in result


class TestDiagnose:
    def test_healthy_empty(self, forge_config):
        d = engine.diagnose()
        assert d["total_issues"] >= 0

    def test_detects_missing_repo(self, forge_config, populated_config):
        d = engine.diagnose()
        types = [i["type"] for i in d["issues"]]
        assert "missing_repo" in types

    def test_detects_no_remote(self, forge_config, populated_config, tmp_git_repo):
        import shutil
        workspace_root = tmp_git_repo.parent.parent / "Workspace"
        workspace_root.mkdir(parents=True, exist_ok=True)
        dest = workspace_root / "noremote"
        shutil.copytree(str(tmp_git_repo), str(dest))
        c = forge_config.load_config()
        forge_config.add_repo(c, {"name": "noremote", "path": str(dest), "provider": "unknown", "url": "", "default_branch": "main"})
        forge_config.save_config(c)
        d = engine.diagnose()
        types = [i["type"] for i in d["issues"]]
        assert "no_remote" in types

    def test_detects_stale_worktree(self, forge_config):
        c = forge_config.load_config()
        forge_config.add_repo(c, {"name": "repo", "path": "/tmp/repo", "provider": "github", "url": "", "default_branch": "main"})
        c.setdefault("features", []).append({"id": "feat-1", "name": "stale", "worktrees": {"repo": "/nonexistent/wt"}})
        forge_config.save_config(c)
        d = engine.diagnose()
        types = [i["type"] for i in d["issues"]]
        assert "stale_worktree" in types


class TestSessionLog:
    def test_list_empty(self, forge_config):
        assert engine.list_sessions() == []

    def test_list_recent(self, forge_config):
        c = forge_config.load_config()
        c.setdefault("sessions", []).append({"id": "sess-1", "agent": "test", "started": "2025-01-01T00:00:00", "context": "hello world this is a test"})
        c["sessions"].append({"id": "sess-2", "agent": "test", "started": "2025-01-02T00:00:00", "context": ""})
        forge_config.save_config(c)
        result = engine.list_sessions(limit=10)
        assert len(result) == 2
        # Most recent first (reversed)
        assert result[0]["id"] == "sess-2"
        assert result[1]["context_preview"] == "hello world this is a test"

    def test_list_limit(self, forge_config):
        c = forge_config.load_config()
        c.setdefault("sessions", [])
        for i in range(5):
            c["sessions"].append({"id": f"sess-{i}", "agent": "test", "started": "", "context": ""})
        forge_config.save_config(c)
        result = engine.list_sessions(limit=3)
        assert len(result) == 3

    def test_get_session_not_found(self, forge_config):
        result = engine.get_session("no-such")
        assert "error" in result

    def test_get_session_from_config(self, forge_config):
        c = forge_config.load_config()
        c.setdefault("sessions", []).append({"id": "sess-1", "agent": "test", "started": "2025-01-01T00:00:00"})
        forge_config.save_config(c)
        result = engine.get_session("sess-1")
        assert "error" not in result
        assert result["session"]["id"] == "sess-1"


class TestValidateConfig:
    def test_config_not_found(self, tmp_path):
        import forge.config as cfg
        cfg.CONFIG_PATH = str(tmp_path / "nonexistent.json")
        result = engine.validate_config()
        assert result["valid"] is False
        assert any("not found" in i["detail"] for i in result["issues"])

    def test_valid_empty(self, forge_config):
        result = engine.validate_config()
        assert result["valid"] is True

    def test_invalid_version(self, forge_config):
        c = forge_config.load_config()
        c["version"] = 99
        forge_config.save_config(c)
        result = engine.validate_config()
        assert any("Unknown config version" in i["detail"] for i in result["issues"])

    def test_missing_workspace_root(self, forge_config):
        c = forge_config.load_config()
        del c["workspace_root"]
        forge_config.save_config(c)
        result = engine.validate_config()
        assert any("Missing workspace_root" in i["detail"] for i in result["issues"])

    def test_duplicate_repo_name(self, forge_config):
        c = forge_config.load_config()
        c["repos"] = [
            {"name": "dup", "path": "/tmp/a"},
            {"name": "dup", "path": "/tmp/b"},
        ]
        forge_config.save_config(c)
        result = engine.validate_config()
        assert any("Duplicate repo name" in i["detail"] for i in result["issues"])

    def test_repo_missing_path(self, forge_config):
        c = forge_config.load_config()
        c["repos"] = [{"name": "nopath"}]
        forge_config.save_config(c)
        result = engine.validate_config()
        assert any("Missing path" in i["detail"] for i in result["issues"])

    def test_repo_path_not_found(self, forge_config):
        c = forge_config.load_config()
        c["repos"] = [{"name": "test", "path": "/nonexistent/path"}]
        forge_config.save_config(c)
        result = engine.validate_config()
        assert any("Path not found" in i["detail"] for i in result["issues"])

    def test_feature_refs_missing_repo(self, forge_config):
        c = forge_config.load_config()
        c["features"] = [{"id": "feat-1", "name": "test", "repos": ["no-such-repo"], "worktrees": {}}]
        forge_config.save_config(c)
        result = engine.validate_config()
        assert any("References missing repo" in i["detail"] for i in result["issues"])

    def test_stale_worktree(self, forge_config):
        c = forge_config.load_config()
        c["features"] = [{"id": "feat-1", "name": "test", "repos": [], "worktrees": {"repo-a": "/nonexistent/wt"}}]
        forge_config.save_config(c)
        result = engine.validate_config()
        assert any("Stale worktree" in i["detail"] for i in result["issues"])

    def test_fix_removes_stale_worktree(self, forge_config):
        c = forge_config.load_config()
        c["features"] = [{"id": "feat-1", "name": "test", "repos": [], "worktrees": {"repo-a": "/nonexistent/wt"}}]
        forge_config.save_config(c)
        result = engine.validate_config(fix=True)
        assert not any("Stale worktree" in i.get("detail", "") for i in result["issues"])
        assert result.get("_repaired")


class TestCreatePrs:
    def test_feature_not_found(self, forge_config):
        result = engine.create_prs("nonexistent")
        assert "error" in result
        assert "not found" in result["error"]

    def test_no_repos_in_feature(self, forge_config):
        engine.add_feature("empty-feat")
        result = engine.create_prs("empty-feat")
        assert "error" in result
        assert "No repos" in result["error"]

    def test_repo_not_found(self, forge_config):
        engine.add_feature("my-feat", repos=["no-such-repo"])
        result = engine.create_prs("my-feat")
        assert "prs" in result
        assert result["prs"][0].get("error") == "Repo not found in workspace config"

    def test_repo_path_not_found(self, forge_config, populated_config):
        engine.add_feature("my-feat", repos=["repo-a"])
        result = engine.create_prs("my-feat")
        assert result["prs"][0].get("error") == "Repo path not found"

    def test_gh_not_installed(self, forge_config, mocker):
        mocker.patch("shutil.which", return_value=None)
        engine.add_feature("my-feat", repos=["repo-a"])
        result = engine.create_prs("my-feat")
        assert "error" in result
        assert "gh) not found" in result["error"]

    def test_branch_not_found(self, forge_config, tmp_git_repo):
        workspace_root = tmp_git_repo.parent.parent / "Workspace"
        workspace_root.mkdir(parents=True, exist_ok=True)
        c = forge_config.load_config()
        forge_config.add_repo(c, {"name": "my-repo", "path": str(tmp_git_repo), "provider": "github", "url": "https://github.com/test/my-repo.git", "default_branch": "main"})
        forge_config.save_config(c)
        engine.add_feature("my-feat", repos=["my-repo"])
        result = engine.create_prs("my-feat")
        assert result["prs"][0].get("error", "").startswith("Branch 'feature/my-feat' not found")

    def test_create_pr_success(self, forge_config, tmp_git_repo, mocker):
        # Create a feature branch in the git repo
        subprocess.run(["git", "checkout", "-b", "feature/my-feat"], cwd=tmp_git_repo, capture_output=True, check=True)
        workspace_root = tmp_git_repo.parent.parent / "Workspace"
        workspace_root.mkdir(parents=True, exist_ok=True)
        c = forge_config.load_config()
        forge_config.add_repo(c, {"name": "my-repo", "path": str(tmp_git_repo), "provider": "github", "url": "https://github.com/test/my-repo.git", "default_branch": "main"})
        forge_config.save_config(c)
        engine.add_feature("my-feat", repos=["my-repo"])
        mocker.patch("shutil.which", return_value="/usr/bin/gh")
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="https://github.com/test/my-repo/pull/1\n", stderr="")
        result = engine.create_prs("my-feat")
        assert "error" not in result
        assert result["prs"][0]["status"] == "created"
        assert result["prs"][0]["url"] == "https://github.com/test/my-repo/pull/1"

    def test_create_pr_draft(self, forge_config, tmp_git_repo, mocker):
        subprocess.run(["git", "checkout", "-b", "feature/draft-feat"], cwd=tmp_git_repo, capture_output=True, check=True)
        workspace_root = tmp_git_repo.parent.parent / "Workspace"
        workspace_root.mkdir(parents=True, exist_ok=True)
        c = forge_config.load_config()
        forge_config.add_repo(c, {"name": "my-repo", "path": str(tmp_git_repo), "provider": "github", "url": "https://github.com/test/my-repo.git", "default_branch": "main"})
        forge_config.save_config(c)
        engine.add_feature("draft-feat", repos=["my-repo"])
        mocker.patch("shutil.which", return_value="/usr/bin/gh")
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="https://github.com/test/my-repo/pull/2\n", stderr="")
        result = engine.create_prs("draft-feat", draft=True)
        assert result["prs"][0]["status"] == "created"
        call_args = mock_run.call_args_list
        # Find the gh pr create call (not git rev-parse or pr edit)
        gh_create_calls = [c for c in call_args if c[0][0][:2] == ["gh", "pr"] and c[0][0][2] == "create"]
        assert len(gh_create_calls) == 1
        assert "--draft" in gh_create_calls[0][0][0]

    def test_cross_reference_multi_repo(self, forge_config, tmp_path, mocker):
        import forge.config as cfg
        # Create two repos
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        for rp in [repo_a, repo_b]:
            rp.mkdir()
            subprocess.run(["git", "init"], cwd=rp, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=rp, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "T"], cwd=rp, capture_output=True, check=True)
            (rp / "README.md").write_text(f"# {rp.name}")
            subprocess.run(["git", "add", "."], cwd=rp, capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=rp, capture_output=True, check=True)
            subprocess.run(["git", "checkout", "-b", "feature/cross"], cwd=rp, capture_output=True, check=True)
        workspace_root = tmp_path / "Workspace"
        workspace_root.mkdir(parents=True, exist_ok=True)
        c = forge_config.load_config()
        cfg.add_repo(c, {"name": "repo-a", "path": str(repo_a), "provider": "github", "url": "https://github.com/test/repo-a.git", "default_branch": "main"})
        cfg.add_repo(c, {"name": "repo-b", "path": str(repo_b), "provider": "github", "url": "https://github.com/test/repo-b.git", "default_branch": "main"})
        cfg.save_config(c)
        engine.add_feature("cross", repos=["repo-a", "repo-b"])
        mocker.patch("shutil.which", return_value="/usr/bin/gh")
        mock_run = mocker.patch("subprocess.run")
        # Return different URLs for each call to gh pr create (which is called after git rev-parse for each repo)
        # First two calls are git rev-parse for repo-a and repo-b
        # Then gh pr create for repo-a, then gh pr create for repo-b, then gh pr edit for both
        mock_run.side_effect = [
            subprocess.CompletedProcess([], 0, stdout="", stderr=""),  # git rev-parse repo-a
            subprocess.CompletedProcess([], 0, stdout="", stderr=""),  # git rev-parse repo-b
            subprocess.CompletedProcess([], 0, stdout="https://github.com/test/repo-a/pull/10\n", stderr=""),  # gh pr create repo-a
            subprocess.CompletedProcess([], 0, stdout="https://github.com/test/repo-b/pull/20\n", stderr=""),  # gh pr create repo-b
            subprocess.CompletedProcess([], 0, stdout="", stderr=""),  # gh pr edit repo-a
            subprocess.CompletedProcess([], 0, stdout="", stderr=""),  # gh pr edit repo-b
        ]
        result = engine.create_prs("cross")
        assert "error" not in result
        assert len(result["prs"]) == 2
        assert result["prs"][0]["cross_referenced"] is True
        assert result["prs"][1]["cross_referenced"] is True
        # Verify gh pr edit was called with cross-refs
        edit_calls = [c for c in mock_run.call_args_list if c[0][0][:3] == ["gh", "pr", "edit"]]
        assert len(edit_calls) == 2
        # repo-a's edit body should reference repo-b (and not itself)
        body_a = edit_calls[0][0][0]
        body_a_text = body_a[body_a.index("--body") + 1]
        assert "Related PRs" in body_a_text
        assert "repo-b" in body_a_text
        # repo-b's edit body should reference repo-a (and not itself)
        body_b = edit_calls[1][0][0]
        body_b_text = body_b[body_b.index("--body") + 1]
        assert "Related PRs" in body_b_text
        assert "repo-a" in body_b_text

    def test_create_pr_custom_body(self, forge_config, tmp_git_repo, mocker):
        subprocess.run(["git", "checkout", "-b", "feature/custom"], cwd=tmp_git_repo, capture_output=True, check=True)
        workspace_root = tmp_git_repo.parent.parent / "Workspace"
        workspace_root.mkdir(parents=True, exist_ok=True)
        c = forge_config.load_config()
        forge_config.add_repo(c, {"name": "my-repo", "path": str(tmp_git_repo), "provider": "github", "url": "https://github.com/test/my-repo.git", "default_branch": "main"})
        forge_config.save_config(c)
        engine.add_feature("custom", repos=["my-repo"])
        mocker.patch("shutil.which", return_value="/usr/bin/gh")
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="https://github.com/test/my-repo/pull/3\n", stderr="")
        engine.create_prs("custom", title="Custom Title", body="Custom body text")
        call_args = mock_run.call_args_list
        gh_create_calls = [c for c in call_args if c[0][0][:3] == ["gh", "pr", "create"]]
        assert len(gh_create_calls) == 1
        create_args = gh_create_calls[0][0][0]
        title_idx = create_args.index("--title") + 1
        body_idx = create_args.index("--body") + 1
        assert create_args[title_idx] == "Custom Title"
        assert create_args[body_idx] == "Custom body text"


class TestAgentHandoff:
    def test_handoff_session_not_found(self):
        result = engine.agent_handoff("nonexistent", "claude")
        assert "error" in result

    def test_handoff_success(self, forge_config, tmp_forge_workspace):
        forge_dir, workspace_root, _ = tmp_forge_workspace
        c = forge_config.load_config()
        c.setdefault("sessions", []).append({
            "id": "sess-test123",
            "agent": "claude",
            "started": "2026-06-08T00:00:00",
            "context": "Working on auth module",
            "feature": "",
        })
        forge_config.save_config(c)
        import json
        meta_path = forge_dir / "sessions" / "sess-test123" / "meta.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_path, "w") as f:
            json.dump({"id": "sess-test123", "agent": "claude"}, f)
        transcript_path = forge_dir / "sessions" / "sess-test123" / "transcript.md"
        with open(transcript_path, "w") as f:
            f.write("This is a transcript of the session.")
        result = engine.agent_handoff("sess-test123", "codex")
        assert result["session_id"] == "sess-test123"
        assert result["handoff_to"] == "codex"
        assert result["transcript_length"] > 0
        assert os.path.exists(result["handoff_md"])
        assert os.path.exists(result["handoff_json"])

    def test_handoff_with_feature(self, forge_config, tmp_forge_workspace):
        forge_dir, workspace_root, _ = tmp_forge_workspace
        c = forge_config.load_config()
        engine.add_feature("login-flow", repos=["repo-a", "repo-b"])
        c = forge_config.load_config()
        feature = c["features"][0]
        feature["decisions"].append({
            "timestamp": "2026-01-01T00:00:00",
            "message": "Use OAuth2 for auth",
            "type": "breaking",
            "author": "bobby",
        })
        forge_config.save_config(c)
        c.setdefault("sessions", []).append({
            "id": "sess-feat456",
            "agent": "codex",
            "started": "2026-06-08T01:00:00",
            "context": "Implementing OAuth2",
            "feature": feature["id"],
        })
        forge_config.save_config(c)
        import json
        meta_path = forge_dir / "sessions" / "sess-feat456" / "meta.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_path, "w") as f:
            json.dump({"id": "sess-feat456", "agent": "codex", "feature": feature["id"]}, f)
        transcript_path = forge_dir / "sessions" / "sess-feat456" / "transcript.md"
        with open(transcript_path, "w") as f:
            f.write("Implementing OAuth2 flow")
        result = engine.agent_handoff("sess-feat456", "claude")
        assert result["decisions_count"] == 1
        md_content = open(result["handoff_md"]).read()
        assert "OAuth2" in md_content


class TestSearchSessions:
    def test_search_empty(self, forge_config):
        assert engine.search_sessions("anything") == []

    def test_search_by_id(self, forge_config):
        c = forge_config.load_config()
        c.setdefault("sessions", []).append({"id": "sess-abc123", "agent": "claude", "context": "", "feature": ""})
        forge_config.save_config(c)
        results = engine.search_sessions("abc123")
        assert len(results) == 1
        assert results[0]["match_field"] == "id"

    def test_search_by_agent(self, forge_config):
        c = forge_config.load_config()
        c.setdefault("sessions", []).append({"id": "sess-1", "agent": "codex", "context": "", "feature": ""})
        c.setdefault("sessions", []).append({"id": "sess-2", "agent": "claude", "context": "", "feature": ""})
        forge_config.save_config(c)
        results = engine.search_sessions("codex")
        assert len(results) == 1

    def test_search_by_context(self, forge_config):
        c = forge_config.load_config()
        c.setdefault("sessions", []).append({"id": "sess-1", "agent": "claude", "context": "Working on OAuth2 authentication", "feature": ""})
        forge_config.save_config(c)
        results = engine.search_sessions("OAuth2")
        assert len(results) == 1
        assert results[0]["match_field"] == "context"

    def test_search_by_transcript(self, forge_config, tmp_forge_workspace):
        forge_dir, _, _ = tmp_forge_workspace
        c = forge_config.load_config()
        c.setdefault("sessions", []).append({"id": "sess-trans", "agent": "claude", "context": "", "feature": ""})
        forge_config.save_config(c)
        import json
        meta_path = forge_dir / "sessions" / "sess-trans" / "meta.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_path, "w") as f:
            json.dump({"id": "sess-trans"}, f)
        transcript_path = forge_dir / "sessions" / "sess-trans" / "transcript.md"
        with open(transcript_path, "w") as f:
            f.write("We decided to use Redis for caching")
        results = engine.search_sessions("Redis")
        assert len(results) == 1
        assert results[0]["match_field"] == "transcript"

    def test_search_limit(self, forge_config):
        c = forge_config.load_config()
        for i in range(5):
            c.setdefault("sessions", []).append({"id": f"sess-{i}", "agent": "claude", "context": "work", "feature": ""})
        forge_config.save_config(c)
        results = engine.search_sessions("work", limit=2)
        assert len(results) == 2


class TestDiffSessions:
    def test_diff_nonexistent(self, forge_config):
        result = engine.diff_sessions("does-not-exist", "also-not")
        assert "error" in result

    def test_diff_same_session(self, forge_config, tmp_forge_workspace):
        forge_dir, _, _ = tmp_forge_workspace
        c = forge_config.load_config()
        c.setdefault("sessions", []).append({"id": "sess-a", "agent": "claude", "context": "Hello", "feature": ""})
        forge_config.save_config(c)
        import json
        meta_path = forge_dir / "sessions" / "sess-a" / "meta.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_path, "w") as f:
            json.dump({"id": "sess-a"}, f)
        transcript_path = forge_dir / "sessions" / "sess-a" / "transcript.md"
        with open(transcript_path, "w") as f:
            f.write("content a")
        result = engine.diff_sessions("sess-a", "sess-a")
        assert "error" not in result
        assert result["transcript_diff_lines"] == 0

    def test_diff_different_sessions(self, forge_config, tmp_forge_workspace):
        forge_dir, _, _ = tmp_forge_workspace
        c = forge_config.load_config()
        c.setdefault("sessions", []).append({"id": "sess-x", "agent": "claude", "context": "Auth module", "feature": ""})
        c.setdefault("sessions", []).append({"id": "sess-y", "agent": "codex", "context": "Caching layer", "feature": ""})
        forge_config.save_config(c)
        import json
        for sid in ("sess-x", "sess-y"):
            meta_path = forge_dir / "sessions" / sid / "meta.json"
            meta_path.parent.mkdir(parents=True, exist_ok=True)
            agent = "claude" if sid == "sess-x" else "codex"
            context = "Auth module" if sid == "sess-x" else "Caching layer"
            with open(meta_path, "w") as f:
                json.dump({"id": sid, "agent": agent, "context": context}, f)
            transcript_path = forge_dir / "sessions" / sid / "transcript.md"
            with open(transcript_path, "w") as f:
                f.write(f"Transcript for {sid}")
        result = engine.diff_sessions("sess-x", "sess-y")
        assert result["agent"]["a"] == "claude"
        assert result["agent"]["b"] == "codex"
        assert result["context"]["a"] == "Auth module"
        assert result["context"]["b"] == "Caching layer"
        assert result["transcript_diff_lines"] > 0
