import json
import os
import pytest
from unittest.mock import mock_open
from ws import install


class TestInstallAgent:
    def test_unknown_agent(self):
        result = install.install_agent("unknown")
        assert "error" in result
        assert "Unknown agent" in result["error"]

    def test_no_node(self, mocker):
        mocker.patch("shutil.which", return_value=None)
        result = install.install_agent("claude")
        assert "error" in result
        assert "Node.js" in result["error"]

    def test_no_npm(self, mocker):
        mocker.patch("shutil.which", side_effect=lambda x: "/usr/bin/node" if x == "node" else None)
        result = install.install_agent("claude")
        assert "error" in result
        assert "npm" in result["error"]

    def test_already_installed(self, mocker):
        mocker.patch("shutil.which", side_effect=lambda x: {
            "node": "/usr/bin/node",
            "npm": "/usr/bin/npm",
            "claude": "/usr/bin/claude",
        }.get(x))
        mocker.patch("os.makedirs")
        mock_file = mock_open(read_data="{}")
        mocker.patch("builtins.open", mock_file)
        result = install.install_agent("claude")
        assert result["success"] is True
        assert "already installed" in result.get("note", "").lower()

    def test_fresh_install_success(self, mocker):
        def which_side(name):
            if name in ("node", "npm"):
                return f"/usr/bin/{name}"
            return None
        mocker.patch("shutil.which", side_effect=which_side)
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = type("Proc", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        mocker.patch("os.makedirs")
        mock_file = mock_open(read_data="{}")
        mocker.patch("builtins.open", mock_file)
        result = install.install_agent("claude")
        assert result["success"] is True
        assert result["agent"] == "claude"
        assert result["binary"] == "claude"
        assert "mcp_config" in result

    def test_install_timeout(self, mocker):
        mocker.patch("shutil.which", side_effect=lambda x: f"/usr/bin/{x}" if x in ("node", "npm") else None)
        mock_run = mocker.patch("subprocess.run", side_effect=__import__("subprocess").TimeoutExpired("cmd", 30))
        result = install.install_agent("codex")
        assert "error" in result


class TestConfigureMCP:
    def test_claude_config_has_ws_server(self, mocker, tmp_path):
        mocker.patch("ws.install._ws_serve_command", return_value=["ws", "serve"])
        fake_config_dir = tmp_path / "claude"
        mocker.patch("ws.install.AGENTS", {"claude": {
            "name": "Claude Code", "npm_package": "@anthropic-ai/claude-code",
            "binary": "claude", "config_dir": str(fake_config_dir),
            "config_file": "claude_desktop_config.json", "mcp_key": "mcpServers",
        }})
        result_path = install._configure_claude_mcp()
        assert os.path.exists(result_path)
        data = json.loads(open(result_path).read())
        assert "mcpServers" in data
        assert "ws" in data["mcpServers"]
        assert data["mcpServers"]["ws"]["command"] == "ws"

    def test_codex_env_has_servers(self, mocker, tmp_path):
        mocker.patch("ws.install._ws_serve_command", return_value=["ws", "serve"])
        fake_config_dir = tmp_path / "codex"
        mocker.patch("ws.install.AGENTS", {"codex": {
            "name": "Codex CLI", "npm_package": "@openai/codex",
            "binary": "codex", "env_var": "CODEX_MCP_SERVERS",
            "config_dir": str(fake_config_dir),
        }})
        result_path = install._configure_codex_env()
        assert os.path.exists(result_path)
        data = json.loads(open(result_path).read())
        assert "CODEX_MCP_SERVERS" in data


class TestInstallCli:
    def test_unknown_agent(self, ws_config, captured_print):
        from ws.cli import cmd_install
        import argparse
        cmd_install(argparse.Namespace(agent="unknown"))
        output = " ".join(captured_print)
        assert "Unknown agent" in output
