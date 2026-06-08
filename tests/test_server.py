import json
import subprocess
import pytest

pytest.importorskip("mcp")


@pytest.fixture
def server():
    from forge.server import app
    return app


class TestListTools:
    def test_list_tools_returns_expected(self):
        from forge.server import list_tools
        import asyncio
        tools = asyncio.run(list_tools())
        names = [t.name for t in tools]
        assert "list_repos" in names
        assert "repo_status" in names
        assert "workspace_status" in names
        assert "workspace_health" in names
        assert "workspace_doctor" in names
        assert "clone_repo" in names
        assert "workspace_scan" in names
        assert "create_feature" in names
        assert "list_features" in names
        assert "log_decision" in names
        assert "get_decisions" in names
        assert "start_session" in names
        assert "share_note" in names
        assert "get_shared_notes" in names
        assert "create_prs" in names
        assert "generate_graph" in names
        assert "validate_config" in names
        assert "generate_completion" in names
        assert "ai_detect" in names
        assert "ai_config" in names
        assert "exec_nl" in names
        assert "ai_setup" in names
        assert "ai_benchmark" in names
        assert "ai_status" in names
        assert "cve_fix_info" in names
        assert "agent_handoff" in names
        assert len(names) == 26

    def test_tool_has_schema(self):
        from forge.server import list_tools
        import asyncio
        tools = asyncio.run(list_tools())
        for t in tools:
            assert t.inputSchema is not None


class TestCallTool:
    @pytest.mark.asyncio
    async def test_list_repos_empty(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("list_repos", {})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data == []

    @pytest.mark.asyncio
    async def test_workspace_status(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("workspace_status", {})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["total_repos"] == 0

    @pytest.mark.asyncio
    async def test_list_features_empty(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("list_features", {})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data == []

    @pytest.mark.asyncio
    async def test_unknown_tool(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("nonexistent", {})
        assert "Unknown tool" in result[0].text

    @pytest.mark.asyncio
    async def test_repo_status_not_found(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("repo_status", {"name": "no-such-repo"})
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_create_feature(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("create_feature", {"name": "test-feat", "repos": []})
        data = json.loads(result[0].text)
        assert data["name"] == "test-feat"
        assert data["id"].startswith("feat-")

    @pytest.mark.asyncio
    async def test_share_and_get_notes(self, forge_config):
        from forge.server import call_tool
        await call_tool("share_note", {"content": "test note", "group": "g2", "label": "mylabel"})
        result = await call_tool("get_shared_notes", {"group": "g2"})
        data = json.loads(result[0].text)
        assert len(data) == 1
        assert data[0]["content"] == "test note"

    @pytest.mark.asyncio
    async def test_log_and_get_decisions(self, forge_config):
        from forge.server import call_tool
        feat = await call_tool("create_feature", {"name": "dec-test", "repos": []})
        fid = json.loads(feat[0].text)["id"]
        await call_tool("log_decision", {"feature_id": fid, "message": "use postgres", "type": "breaking", "author": "alice"})
        result = await call_tool("get_decisions", {"feature_id": fid})
        data = json.loads(result[0].text)
        assert len(data) == 1
        assert data[0]["message"] == "use postgres"

    @pytest.mark.asyncio
    async def test_log_decision_missing_feature(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("log_decision", {"feature_id": "feat-noexist", "message": "x", "type": "info", "author": "me"})
        assert "not found" in result[0].text

    @pytest.mark.asyncio
    async def test_get_decisions_missing_feature(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("get_decisions", {"feature_id": "feat-noexist"})
        assert result[0].text == "[]"

    @pytest.mark.asyncio
    async def test_start_session(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("start_session", {"agent": "claude-code", "context": "fix auth", "feature_id": ""})
        data = json.loads(result[0].text)
        assert data["session_id"].startswith("sess-")

    @pytest.mark.asyncio
    async def test_error_returns_text(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("repo_status", {"name": None})
        assert len(result) == 1
        assert isinstance(result[0].text, str)

    @pytest.mark.asyncio
    async def test_generate_graph(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("generate_graph", {"name": "no-such-repo"})
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_validate_config_empty(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("validate_config", {})
        data = json.loads(result[0].text)
        assert data["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_config_with_fix(self, forge_config):
        from forge.server import call_tool
        c = forge_config.load_config()
        c["features"] = [{"id": "feat-stale", "name": "stale", "repos": [], "worktrees": {"r": "/nonexistent/wt"}}]
        forge_config.save_config(c)
        result = await call_tool("validate_config", {"fix": True})
        data = json.loads(result[0].text)
        assert data["valid"] is True
        assert data.get("_repaired")

    @pytest.mark.asyncio
    async def test_generate_completion_bash(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("generate_completion", {"shell": "bash"})
        assert "_forge_completions" in result[0].text

    @pytest.mark.asyncio
    async def test_generate_completion_zsh(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("generate_completion", {"shell": "zsh"})
        assert "#compdef forge" in result[0].text

    @pytest.mark.asyncio
    async def test_ai_detect(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("ai_detect", {})
        data = json.loads(result[0].text)
        assert "cpu" in data
        assert "memory" in data
        assert "gpu" in data

    @pytest.mark.asyncio
    async def test_ai_config_show(self, forge_config):
        from forge.server import call_tool
        c = forge_config.load_config()
        c["ai"] = {"provider": "ollama"}
        forge_config.save_config(c)
        result = await call_tool("ai_config", {})
        data = json.loads(result[0].text)
        assert data["provider"] == "ollama"

    @pytest.mark.asyncio
    async def test_ai_config_set(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("ai_config", {"key": "provider", "value": "test"})
        data = json.loads(result[0].text)
        assert data["provider"] == "test"

    @pytest.mark.asyncio
    async def test_exec_nl_dry_run(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("exec_nl", {"query": "status", "dry_run": True})
        data = json.loads(result[0].text)
        assert data["intent"] == "status"
        assert data["command"] == "forge status"

    @pytest.mark.asyncio
    async def test_exec_nl_unknown(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("exec_nl", {"query": "do something crazy", "dry_run": False})
        data = json.loads(result[0].text)
        assert "intent" in data or "error" in data

    @pytest.mark.asyncio
    async def test_ai_setup_ollama(self, forge_config, mocker):
        from forge.server import call_tool
        mocker.patch("forge.ai.check_ollama", return_value=True)
        mocker.patch("forge.ai.detect_hardware", return_value={
            "recommended_backend": "ollama", "apple_silicon": False,
            "memory": {"total_gb": 8}, "gpu": [{"vendor": "none", "model": "none"}],
        })
        mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""))
        result = await call_tool("ai_setup", {"backend": "ollama"})
        data = json.loads(result[0].text)
        assert data.get("backend") == "ollama"

    @pytest.mark.asyncio
    async def test_ai_benchmark_no_model(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("ai_benchmark", {})
        data = json.loads(result[0].text)
        assert "error" in data or "model" in data

    @pytest.mark.asyncio
    async def test_ai_status(self, forge_config):
        from forge.server import call_tool
        result = await call_tool("ai_status", {"backend": "ollama"})
        data = json.loads(result[0].text)
        assert "ready" in data
