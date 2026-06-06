import argparse
import json
import pytest
from ws.cli import cmd_status, cmd_health, cmd_config_path, cmd_scan, cmd_init, cmd_share, cmd_notes, cmd_feature, cmd_doctor


def _ns(**kw):
    return argparse.Namespace(**kw)


class TestCmdConfigPath:
    def test_prints_config_path(self, ws_config, captured_print):
        cmd_config_path(_ns())
        assert len(captured_print) == 1
        assert captured_print[0].endswith("config.json")


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
        cmd_status(_ns(name=None, json=False))
        output = " ".join(captured_print)
        assert "Workspace" in output
        assert "0 total" in output

    def test_status_json(self, ws_config, captured_print):
        cmd_status(_ns(name=None, json=True))
        assert len(captured_print) == 1
        data = json.loads(captured_print[0])
        assert "total_repos" in data
        assert "repos" in data


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
