import json
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from . import config as cfg
from . import engine
from . import git
from . import graph as wsgraph
from . import ai as wsai
from .cli import _completion_script

app = Server("ws")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_repos",
            description="List all registered workspace repositories",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="repo_status",
            description="Get git status for a repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Repository name"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="workspace_status",
            description="Get overall workspace status across all repos",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="workspace_health",
            description="Check dev environment health (brew, ollama, gh, disk)",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="workspace_doctor",
            description="Diagnose workspace issues (missing repos, stale worktrees, no remotes)",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="clone_repo",
            description="Clone a repository into the workspace",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Repository URL"},
                    "name": {"type": "string", "description": "Override repo name (optional)"},
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="workspace_scan",
            description="Scan workspace root for new git repositories",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="create_feature",
            description="Create a named feature with optional repo list",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Feature name"},
                    "repos": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Repo names involved (optional)",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="list_features",
            description="List all active features",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="log_decision",
            description="Log a cross-worktree decision for a feature",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_id": {"type": "string", "description": "Feature ID"},
                    "message": {"type": "string", "description": "Decision description"},
                    "type": {
                        "type": "string",
                        "description": "Decision type (info, breaking, review)",
                        "enum": ["info", "breaking", "review"],
                    },
                    "author": {"type": "string", "description": "Who made the decision"},
                },
                "required": ["feature_id", "message", "type", "author"],
            },
        ),
        Tool(
            name="get_decisions",
            description="Get all decisions logged for a feature",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_id": {"type": "string", "description": "Feature ID"},
                },
                "required": ["feature_id"],
            },
        ),
        Tool(
            name="start_session",
            description="Record the start of an agent session",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_id": {"type": "string", "description": "Feature ID (optional)"},
                    "agent": {"type": "string", "description": "Agent name (claude-code, codex, etc)"},
                    "context": {"type": "string", "description": "Session context/prompt"},
                },
                "required": ["agent"],
            },
        ),
        Tool(
            name="share_note",
            description="Share a note across projects in a group",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Note content"},
                    "group": {"type": "string", "description": "Group name"},
                    "label": {"type": "string", "description": "Optional label"},
                },
                "required": ["content", "group"],
            },
        ),
        Tool(
            name="get_shared_notes",
            description="Get shared notes for a group",
            inputSchema={
                "type": "object",
                "properties": {
                    "group": {"type": "string", "description": "Group name"},
                },
                "required": ["group"],
            },
        ),
        Tool(
            name="generate_graph",
            description="Generate a knowledge graph for a workspace repo (co-change or branches)",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Repository name"},
                    "graph_type": {
                        "type": "string",
                        "enum": ["co-change", "branches"],
                        "description": "Type of graph to generate",
                    },
                    "depth": {"type": "integer", "description": "Commits to analyze (default 50)"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="create_prs",
            description="Create PRs across all repos in a feature with cross-references",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_id": {"type": "string", "description": "Feature name or ID"},
                    "title": {"type": "string", "description": "PR title (optional)"},
                    "body": {"type": "string", "description": "PR body text (optional)"},
                    "draft": {"type": "boolean", "description": "Create as draft PR"},
                },
                "required": ["feature_id"],
            },
        ),
        Tool(
            name="validate_config",
            description="Validate workspace configuration and optionally repair issues",
            inputSchema={
                "type": "object",
                "properties": {
                    "fix": {"type": "boolean", "description": "Auto-repair fixable issues (stale worktrees)"},
                },
            },
        ),
        Tool(
            name="generate_completion",
            description="Generate shell completion script for bash, zsh, or fish",
            inputSchema={
                "type": "object",
                "properties": {
                    "shell": {
                        "type": "string",
                        "enum": ["bash", "zsh", "fish"],
                        "description": "Shell type",
                    },
                },
                "required": ["shell"],
            },
        ),
        Tool(
            name="ai_detect",
            description="Detect hardware profile (CPU, RAM, GPU, disk)",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="ai_config",
            description="View or modify AI configuration in workspace config",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Config key (dot-separated for nested)"},
                    "value": {"type": "string", "description": "Config value (omit to unset)"},
                },
            },
        ),
        Tool(
            name="exec_nl",
            description="Execute a natural language workspace command",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query"},
                    "dry_run": {"type": "boolean", "description": "Show intent without executing"},
                },
                "required": ["query"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "list_repos":
            c = cfg.load_config()
            repos = [{"name": r["name"], "path": r["path"], "provider": r.get("provider")} for r in c.get("repos", [])]
            return [TextContent(type="text", text=json.dumps(repos, indent=2))]

        elif name == "repo_status":
            statuses = engine.get_status(arguments.get("name"))
            return [TextContent(type="text", text=json.dumps(statuses, indent=2, default=str))]

        elif name == "workspace_status":
            status = engine.get_overall_status()
            return [TextContent(type="text", text=json.dumps(status, indent=2, default=str))]

        elif name == "workspace_health":
            h = engine.health_check()
            return [TextContent(type="text", text=json.dumps(h, indent=2))]

        elif name == "workspace_doctor":
            d = engine.diagnose()
            return [TextContent(type="text", text=json.dumps(d, indent=2, default=str))]

        elif name == "clone_repo":
            url = arguments["url"]
            clone_name: str | None = arguments.get("name")
            target = cfg.WORKSPACE_ROOT
            if not clone_name:
                clone_name = url.rstrip("/").split("/")[-1]
                if clone_name.endswith(".git"):
                    clone_name = clone_name[:-4]
            result = git.clone(url, target, clone_name)
            if result.startswith("error"):
                return [TextContent(type="text", text=result)]
            repo = {
                "name": clone_name,
                "path": result,
                "provider": git._detect_provider(url),
                "url": url,
                "default_branch": "main",
            }
            c = cfg.load_config()
            cfg.add_repo(c, repo)
            cfg.save_config(c)
            return [TextContent(type="text", text=json.dumps({"status": "cloned", "path": result, "name": clone_name}))]

        elif name == "workspace_scan":
            added, total = engine.scan_workspace()
            return [TextContent(type="text", text=json.dumps({"total": total, "new": added}))]

        elif name == "create_feature":
            feat = engine.add_feature(arguments["name"], arguments.get("repos", []))
            return [TextContent(type="text", text=json.dumps(feat, indent=2))]

        elif name == "list_features":
            features = engine.list_features()
            return [TextContent(type="text", text=json.dumps(features, indent=2))]

        elif name == "log_decision":
            c = cfg.load_config()
            for f in c.get("features", []):
                if f["id"] == arguments["feature_id"]:
                    decision = {
                        "timestamp": cfg.now_iso(),
                        "message": arguments["message"],
                        "type": arguments.get("type", "info"),
                        "author": arguments.get("author", "unknown"),
                    }
                    f.setdefault("decisions", []).append(decision)
                    cfg.save_config(c)
                    return [TextContent(type="text", text=json.dumps(decision, indent=2))]
            return [TextContent(type="text", text=f"Feature not found: {arguments['feature_id']}")]

        elif name == "get_decisions":
            c = cfg.load_config()
            for f in c.get("features", []):
                if f["id"] == arguments["feature_id"]:
                    return [TextContent(type="text", text=json.dumps(f.get("decisions", []), indent=2))]
            return [TextContent(type="text", text="[]")]

        elif name == "start_session":
            import uuid
            sid = f"sess-{uuid.uuid4().hex[:12]}"
            session = {
                "id": sid,
                "feature": arguments.get("feature_id", ""),
                "agent": arguments["agent"],
                "started": cfg.now_iso(),
                "context": arguments.get("context", ""),
                "worktrees": [],
            }
            c = cfg.load_config()
            c.setdefault("sessions", []).append(session)
            cfg.save_config(c)

            session_dir = os.path.join(cfg.WORKSPACE_DIR, "sessions", sid)
            cfg.ensure_dir(session_dir)
            with open(os.path.join(session_dir, "meta.json"), "w") as f:
                json.dump(session, f, indent=2)
            with open(os.path.join(session_dir, "transcript.md"), "w") as f:
                f.write(f"# Session: {sid}\n\n")
                f.write(f"Agent: {arguments['agent']}\n")
                f.write(f"Started: {session['started']}\n")
                if arguments.get("context"):
                    f.write(f"\n## Context\n\n{arguments['context']}\n")

            return [TextContent(type="text", text=json.dumps({"session_id": sid}, indent=2))]

        elif name == "share_note":
            c = cfg.load_config()
            groups = c.setdefault("groups", [])
            group_name = arguments["group"]
            group = None
            for g in groups:
                if g["name"] == group_name:
                    group = g
                    break
            if not group:
                group = {"name": group_name, "repos": [], "notes": []}
                groups.append(group)
            group.setdefault("notes", []).append({
                "content": arguments["content"],
                "label": arguments.get("label", ""),
                "timestamp": cfg.now_iso(),
            })
            cfg.save_config(c)
            return [TextContent(type="text", text=json.dumps({"status": "shared", "group": group_name}))]

        elif name == "get_shared_notes":
            c = cfg.load_config()
            for g in c.get("groups", []):
                if g["name"] == arguments["group"]:
                    return [TextContent(type="text", text=json.dumps(g.get("notes", []), indent=2))]
            return [TextContent(type="text", text="[]")]

        elif name == "generate_graph":
            result = wsgraph.generate_graph(
                arguments["name"],
                graph_type=arguments.get("graph_type", "co-change"),
                depth=arguments.get("depth", 50),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        elif name == "create_prs":
            result = engine.create_prs(
                arguments["feature_id"],
                title=arguments.get("title"),
                body=arguments.get("body"),
                draft=arguments.get("draft", False),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        elif name == "validate_config":
            result = engine.validate_config(fix=arguments.get("fix", False))
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        elif name == "generate_completion":
            script = _completion_script(arguments["shell"])
            return [TextContent(type="text", text=script)]

        elif name == "ai_detect":
            profile = wsai.detect_hardware()
            return [TextContent(type="text", text=json.dumps(profile, indent=2))]

        elif name == "ai_config":
            c = cfg.load_config()
            ai = c.setdefault("ai", {})
            key = arguments.get("key")
            value = arguments.get("value")
            if key is None:
                return [TextContent(type="text", text=json.dumps(ai, indent=2))]
            keys = key.split(".")
            target = ai
            for k in keys[:-1]:
                target = target.setdefault(k, {})
            if value is not None:
                target[keys[-1]] = value
                cfg.save_config(c)
            elif keys[-1] in target:
                del target[keys[-1]]
                cfg.save_config(c)
            return [TextContent(type="text", text=json.dumps(ai, indent=2))]

        elif name == "exec_nl":
            result = wsai.exec_nl(arguments["query"], dry_run=arguments.get("dry_run", False))
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


async def run_server():
    async with stdio_server() as streams:
        await app.run(
            streams[0],
            streams[1],
            app.create_initialization_options(),
        )
