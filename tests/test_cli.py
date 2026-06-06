import argparse
import json
from ws.cli import cmd_ai, cmd_exec, cmd_completion, cmd_status, cmd_health, cmd_config_path, cmd_scan, cmd_init, cmd_share, cmd_notes, cmd_feature, cmd_doctor, cmd_pr, cmd_graph, cmd_log


def _ns(**kw):
    return argparse.Namespace(**kw)


class TestCmdConfigPath:
    def test_prints_config_path(self, ws_config, captured_print):
        cmd_config_path(_ns(sub="path", fix=False))
        assert len(captured_print) == 1
        assert captured_print[0].endswith("config.json")

    def test_config_validate_empty(self, ws_config, captured_print):
        cmd_config_path(_ns(sub="validate", fix=False))
        output = " ".join(captured_print)
        assert "valid" in output.lower()

    def test_config_validate_with_issues(self, ws_config, captured_print):
        c = ws_config.load_config()
        c["repos"] = [{"name": "orphan", "path": "/nonexistent"}]
        ws_config.save_config(c)
        cmd_config_path(_ns(sub="validate", fix=False))
        output = " ".join(captured_print)
        assert "warning" in output.lower() or "Path not found" in output


class TestCmdCompletion:
    def test_bash_completion(self, captured_print):
        cmd_completion(_ns(shell="bash"))
        output = " ".join(captured_print)
        assert "_ws_completions" in output
        assert "complete -F _ws_completions ws" in output

    def test_zsh_completion(self, captured_print):
        cmd_completion(_ns(shell="zsh"))
        output = " ".join(captured_print)
        assert "#compdef ws" in output

    def test_fish_completion(self, captured_print):
        cmd_completion(_ns(shell="fish"))
        output = " ".join(captured_print)
        assert "_ws_completions" in output

    def test_unsupported_shell(self, captured_print):
        cmd_completion(_ns(shell="bash"))
        output = " ".join(captured_print)
        assert "bash" in output


class TestCmdHealth:
    def test_prints_health(self, captured_print):
        cmd_health(_ns())
        output = " ".join(captured_print)
        assert "brew" in output
        assert "ollama" in output
        assert "python3" in output
        assert "Disk" in output


class TestCmdInit:
    def test_prints_init_message(self, ws_config, captured_print):
        cmd_init(_ns(provider=None))
        output = " ".join(captured_print)
        assert "Initialized workspace" in output


class TestCmdScan:
    def test_scan_empty(self, ws_config, captured_print):
        cmd_scan(_ns())
        output = " ".join(captured_print)
        assert "Scanned" in output
        assert "No new repos" in output


class TestCmdStatus:
    def test_status_empty(self, ws_config, captured_print):
        cmd_status(_ns(name=None, json=False, graph=False))
        output = " ".join(captured_print)
        assert "Workspace" in output
        assert "0 total" in output

    def test_status_json(self, ws_config, captured_print):
        cmd_status(_ns(name=None, json=True, graph=False))
        assert len(captured_print) == 1
        data = json.loads(captured_print[0])
        assert "total_repos" in data
        assert "repos" in data

    def test_status_with_graph(self, ws_config, populated_config, captured_print, mocker):
        mocker.patch("ws.engine.get_overall_status", return_value={
            "total_repos": 2, "dirty": 2, "ahead": 0, "behind": 0, "missing": 0,
            "active_features": 0, "active_sessions": 0,
            "repos": [
                {"name": "repo-a", "path": "/tmp/repo-a", "exists": True, "dirty": True, "branch": "main",
                 "has_remote": True, "remote_url": "https://github.com/test/repo-a.git", "has_upstream": True,
                 "ahead": 0, "behind": 0, "changed_files": 2, "last_commit_msg": "wip"},
                {"name": "repo-b", "path": "/tmp/repo-b", "exists": True, "dirty": True, "branch": "main",
                 "has_remote": True, "remote_url": "https://github.com/test/repo-b.git", "has_upstream": True,
                 "ahead": 0, "behind": 0, "changed_files": 1, "last_commit_msg": "wip2"},
            ],
        })
        mocker.patch("ws.graph.cross_repo_impact", return_value=[
            {"repo_a": "repo-a", "repo_b": "repo-b", "shared_count": 3, "shared_files": ["a.py", "b.py", "c.py"]},
        ])
        cmd_status(_ns(name=None, json=False, graph=True))
        output = " ".join(captured_print)
        assert "cross-repo" in output.lower() or "Cross-repo" in output
        assert "repo-a" in output
        assert "repo-b" in output


class TestCmdShare:
    def test_share_note(self, ws_config, captured_print):
        cmd_share(_ns(content="hello world", group="test-group", label="test-label"))
        output = " ".join(captured_print)
        assert "Shared note" in output

    def test_share_default_group(self, ws_config, captured_print):
        cmd_share(_ns(content="note", group="default", label=""))
        output = " ".join(captured_print)
        assert "Shared note" in output


class TestCmdNotes:
    def test_notes_empty_group(self, ws_config, captured_print):
        cmd_notes(_ns(group="empty-group"))
        output = " ".join(captured_print)
        assert "not found" in output or "No notes" in output

    def test_notes_with_content(self, ws_config, captured_print):
        cmd_share(_ns(content="stored note", group="g1", label="l1"))
        captured_print.clear()
        cmd_notes(_ns(group="g1"))
        output = " ".join(captured_print)
        assert "stored note" in output
        assert "l1" in output


class TestCmdDoctor:
    def test_doctor_empty(self, ws_config, captured_print):
        cmd_doctor(_ns(json=False))
        output = " ".join(captured_print)
        assert "healthy" in output or "issue" in output

    def test_doctor_json(self, ws_config, captured_print):
        cmd_doctor(_ns(json=True))
        import json as j
        data = j.loads(captured_print[0])
        assert "total_issues" in data
        assert "issues" in data


class TestCmdFeature:
    def test_create_and_done(self, ws_config, captured_print):
        cmd_feature(_ns(action="create", name="test-feat", repos="repo-a,repo-b", repo=None))
        output = " ".join(captured_print)
        assert "Created feature" in output

    def test_done_nonexistent(self, ws_config, captured_print):
        cmd_feature(_ns(action="done", name="no-such-feature", repos=None, repo=None))
        output = " ".join(captured_print)
        assert "not found" in output

    def test_list_empty(self, ws_config, captured_print):
        cmd_feature(_ns(action="list", name=None, repos=None, repo=None))
        output = " ".join(captured_print)
        assert "No features" in output


class TestCmdLog:
    def test_log_empty(self, ws_config, captured_print):
        cmd_log(_ns(name=None, limit=10, json=False))
        output = " ".join(captured_print)
        assert "No sessions" in output

    def test_log_json_empty(self, ws_config, captured_print):
        cmd_log(_ns(name=None, limit=10, json=True))
        import json as j
        data = j.loads(captured_print[0])
        assert data == []

    def test_log_with_session(self, ws_config, captured_print):
        c = ws_config.load_config()
        c.setdefault("sessions", []).append({
            "id": "sess-001", "agent": "claude-code", "feature": "feat-1",
            "started": "2025-01-01T00:00:00", "context": "fix auth bug",
        })
        ws_config.save_config(c)
        cmd_log(_ns(name=None, limit=10, json=False))
        output = " ".join(captured_print)
        assert "sess-001" in output
        assert "claude-code" in output

    def test_log_session_detail(self, ws_config, captured_print, mocker):
        c = ws_config.load_config()
        c.setdefault("sessions", []).append({
            "id": "sess-001", "agent": "claude-code", "feature": "feat-1",
            "started": "2025-01-01T00:00:00", "context": "fix auth bug",
        })
        ws_config.save_config(c)
        mocker.patch("ws.engine.get_session", return_value={
            "session": {"id": "sess-001", "agent": "claude-code", "started": "2025-01-01T00:00:00", "context": "fix auth"},
            "transcript": "## Session\n\nAgent: claude-code\nStarted: 2025-01-01T00:00:00\n\n## Context\n\nfix auth",
        })
        cmd_log(_ns(name="sess-001", limit=10, json=False))
        output = " ".join(captured_print)
        assert "sess-001" in output
        assert "Transcript" in output
        assert "claude-code" in output

    def test_log_session_not_found(self, ws_config, captured_print):
        cmd_log(_ns(name="no-such-session", limit=10, json=False))
        output = " ".join(captured_print)
        assert "not found" in output

    def test_log_session_detail_json(self, ws_config, captured_print, mocker):
        mocker.patch("ws.engine.get_session", return_value={
            "session": {"id": "sess-001", "agent": "claude-code"},
            "transcript": "hello",
        })
        cmd_log(_ns(name="sess-001", limit=10, json=True))
        import json as j
        data = j.loads(captured_print[0])
        assert data["session"]["id"] == "sess-001"


class TestCmdGraph:
    def test_graph_repo_not_found(self, ws_config, captured_print):
        cmd_graph(_ns(name="no-such", type="co-change", format="text", depth=50))
        output = " ".join(captured_print)
        assert "not found" in output

    def test_graph_prints_results(self, ws_config, captured_print, mocker):
        mocker.patch("ws.graph.generate_graph", return_value={
            "repo": "my-repo",
            "nodes": [{"id": "a.py", "commits": 3}, {"id": "b.py", "commits": 2}],
            "edges": [{"source": "a.py", "target": "b.py", "weight": 2}],
        })
        cmd_graph(_ns(name="my-repo", type="co-change", format="text", depth=50))
        output = " ".join(captured_print)
        assert "my-repo" in output
        assert "a.py" in output
        assert "b.py" in output
        assert "2x" in output

    def test_graph_json(self, ws_config, captured_print, mocker):
        mocker.patch("ws.graph.generate_graph", return_value={
            "repo": "my-repo",
            "nodes": [],
            "edges": [],
        })
        cmd_graph(_ns(name="my-repo", type="co-change", format="json", depth=50))
        import json as j
        data = j.loads(captured_print[0])
        assert data["repo"] == "my-repo"

    def test_graph_branches_text(self, ws_config, captured_print, mocker):
        mocker.patch("ws.graph.generate_graph", return_value={
            "repo": "my-repo",
            "branches": ["main", "feature/x"],
            "current": "main",
            "history": "* main commit",
        })
        cmd_graph(_ns(name="my-repo", type="branches", format="text", depth=50))
        output = " ".join(captured_print)
        assert "main" in output
        assert "feature/x" in output
        assert "commit" in output


class TestCmdPr:
    def test_pr_create_feature_not_found(self, ws_config, captured_print):
        cmd_pr(_ns(action="create", name="no-such", title=None, body=None, draft=False))
        output = " ".join(captured_print)
        assert "not found" in output

    def test_pr_create_no_repos(self, ws_config, captured_print):
        cmd_feature(_ns(action="create", name="empty", repos=None, repo=None))
        captured_print.clear()
        cmd_pr(_ns(action="create", name="empty", title=None, body=None, draft=False))
        output = " ".join(captured_print)
        assert "No repos" in output

    def test_pr_create_prints_results(self, ws_config, captured_print, mocker):
        mocker.patch("ws.engine.create_prs", return_value={
            "feature": "my-feat",
            "id": "feat-123",
            "prs": [
                {"repo": "repo-a", "url": "https://github.com/test/repo-a/pull/1", "status": "created", "cross_referenced": True},
                {"repo": "repo-b", "url": "https://github.com/test/repo-b/pull/2", "status": "created", "cross_referenced": False},
            ],
        })
        cmd_pr(_ns(action="create", name="my-feat", title="My Title", body="My Body", draft=False))
        output = " ".join(captured_print)
        assert "my-feat" in output
        assert "feat-123" in output
        assert "repo-a" in output
        assert "repo-b" in output
        assert "pull/1" in output
        assert "cross-ref" in output


class TestCmdAiDetect:
    def test_detect_json(self, ws_config, captured_print):
        cmd_ai(_ns(action="detect", json=True, model="", prompt="", backend="", key=None, value=None))
        output = " ".join(captured_print)
        assert "cpu" in output
        assert "memory" in output

    def test_detect_text(self, ws_config, captured_print):
        cmd_ai(_ns(action="detect", json=False, model="", prompt="", backend="", key=None, value=None))
        output = " ".join(captured_print)
        assert "Hardware Profile" in output
        assert "CPU" in output


class TestCmdAiConfig:
    def test_config_show(self, ws_config, captured_print):
        c = ws_config.load_config()
        c["ai"] = {"provider": "ollama"}
        ws_config.save_config(c)
        cmd_ai(_ns(action="config", json=False, model="", prompt="", key=None, value=None))
        output = " ".join(captured_print)
        assert "ollama" in output

    def test_config_set(self, ws_config, captured_print):
        cmd_ai(_ns(action="config", json=False, model="", prompt="", key="provider", value="ollama"))
        output = " ".join(captured_print)
        assert "provider" in output


class TestCmdExec:
    def test_exec_unknown(self, captured_print):
        cmd_exec(_ns(query="do something impossible", dry_run=False))
        output = " ".join(captured_print)
        assert "Could not understand" in output or "couldn't understand" in output

    def test_exec_dry_run(self, captured_print):
        cmd_exec(_ns(query="status", dry_run=True))
        output = " ".join(captured_print)
        assert "Intent:" in output
        assert "ws status" in output
