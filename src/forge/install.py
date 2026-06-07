import os
import json
import shutil
import subprocess


AGENTS = {
    "claude": {
        "name": "Claude Code",
        "npm_package": "@anthropic-ai/claude-code",
        "binary": "claude",
        "config_dir": "~/.config/claude",
        "config_file": "claude_desktop_config.json",
        "mcp_key": "mcpServers",
    },
    "codex": {
        "name": "Codex CLI",
        "npm_package": "@openai/codex",
        "binary": "codex",
        "env_var": "CODEX_MCP_SERVERS",
        "config_dir": "~/.config/codex",
    },
}


def _forge_serve_command():
    forge_path = shutil.which("forge") or "forge"
    return [forge_path, "serve"]


def _check_npm():
    return shutil.which("npm") is not None


def _check_node():
    return shutil.which("node") is not None


def _npm_install_global(package):
    try:
        r = subprocess.run(
            ["npm", "install", "-g", package],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0:
            return {"success": True}
        return {"success": False, "error": r.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "npm install timed out"}
    except FileNotFoundError:
        return {"success": False, "error": "npm not found"}


def _configure_claude_mcp():
    config_dir = os.path.expanduser("~/.config/claude")
    config_file = os.path.join(config_dir, "claude_desktop_config.json")
    os.makedirs(config_dir, exist_ok=True)

    config = {"mcpServers": {}}
    if os.path.exists(config_file):
        try:
            with open(config_file) as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    config.setdefault("mcpServers", {})
    forge_cmd = _forge_serve_command()
    config["mcpServers"]["forge"] = {
        "command": forge_cmd[0],
        "args": forge_cmd[1:],
    }

    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    return config_file


def _configure_codex_env():
    forge_cmd = _forge_serve_command()
    servers = json.dumps([{"command": forge_cmd[0], "args": forge_cmd[1]}])
    config_dir = os.path.expanduser("~/.config/codex")
    os.makedirs(config_dir, exist_ok=True)
    env_file = os.path.join(config_dir, "env.json")
    env = {}
    if os.path.exists(env_file):
        try:
            with open(env_file) as f:
                env = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    env["CODEX_MCP_SERVERS"] = servers
    with open(env_file, "w") as f:
        json.dump(env, f, indent=2)
    return env_file


def _check_installed(binary):
    return shutil.which(binary) is not None


def install_agent(agent_name):
    agent = AGENTS.get(agent_name)
    if not agent:
        return {"error": f"Unknown agent: {agent_name}. Supported: {', '.join(AGENTS.keys())}"}

    if not _check_node():
        return {"error": "Node.js is required but not found. Install with: brew install node"}
    if not _check_npm():
        return {"error": "npm is required but not found"}

    already_installed = _check_installed(agent["binary"])
    if already_installed:
        install_result = {"success": True, "note": f"{agent['name']} is already installed"}
    else:
        install_result = _npm_install_global(agent["npm_package"])
        if not install_result["success"]:
            return install_result

    note = install_result.get("note", f"{agent['name']} ready")

    if agent_name == "claude":
        config_path = _configure_claude_mcp()
        return {
            "success": True,
            "agent": agent_name,
            "binary": agent["binary"],
            "note": note,
            "mcp_config": config_path,
        }
    elif agent_name == "codex":
        config_path = _configure_codex_env()
        return {
            "success": True,
            "agent": agent_name,
            "binary": agent["binary"],
            "note": note,
            "env_config": config_path,
        }

    return {"success": True, "agent": agent_name}
