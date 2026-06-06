import json
import os
import platform
import shutil
import subprocess
import sys
from . import config as cfg


def detect_hardware():
    profile = {
        "platform": platform.system(),
        "arch": platform.machine(),
        "python_version": sys.version.split()[0],
    }
    profile["cpu"] = _detect_cpu()
    profile["memory"] = _detect_memory()
    profile["gpu"] = _detect_gpu()
    profile["disk"] = _detect_disk()
    return profile


def _detect_cpu():
    info = {"cores": os.cpu_count() or 0}
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    info["model"] = line.split(":", 1)[1].strip()
                    break
    except FileNotFoundError:
        try:
            out = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True, timeout=5)
            if out.returncode == 0 and out.stdout.strip():
                info["model"] = out.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    return info


def _detect_memory():
    info = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    info["total_gb"] = round(kb / (1024 * 1024), 1)
                elif line.startswith("MemAvailable:"):
                    kb = int(line.split()[1])
                    info["available_gb"] = round(kb / (1024 * 1024), 1)
    except FileNotFoundError:
        pass
    return info


def _detect_gpu():
    gpus = []
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            for line in out.stdout.strip().split("\n"):
                if line.strip():
                    parts = [p.strip() for p in line.split(",")]
                    gpu = {"vendor": "nvidia", "model": parts[0]}
                    if len(parts) > 1:
                        gpu["memory"] = parts[1]
                    gpus.append(gpu)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    if not gpus:
        try:
            out = subprocess.run(["rocm-smi", "--showproductname"], capture_output=True, text=True, timeout=10)
            if out.returncode == 0:
                for line in out.stdout.strip().split("\n"):
                    if "GPU" in line and ":" in line:
                        gpus.append({"vendor": "amd", "model": line.split(":", 1)[1].strip()})
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    if not gpus:
        gpus.append({"vendor": "none", "model": "No discrete GPU detected"})
    return gpus


def _detect_disk():
    info = {}
    target = cfg.WORKSPACE_ROOT
    try:
        usage = shutil.disk_usage(target)
        info["total_gb"] = round(usage.total / (1024**3), 1)
        info["free_gb"] = round(usage.free / (1024**3), 1)
        info["used_pct"] = round((usage.used / usage.total) * 100, 1)
    except FileNotFoundError:
        pass
    return info


def suggest_model(profile):
    mem = profile.get("memory", {}).get("total_gb", 0)
    gpu = profile.get("gpu", [])
    has_nvidia = any(g.get("vendor") == "nvidia" for g in gpu)
    if has_nvidia:
        return "qwen2.5-coder:1.5b"
    if mem >= 16:
        return "qwen2.5-coder:7b"
    if mem >= 8:
        return "phi-4-mini:3.8b"
    return "qwen2.5-coder:1.5b"


def check_ollama():
    return bool(shutil.which("ollama"))


def detect_and_print(args):
    profile = detect_hardware()
    if args.json:
        print(json.dumps(profile, indent=2))
        return
    print("\033[36mHardware Profile\033[0m")
    print(f"  Platform:  {profile['platform']} ({profile['arch']})")
    cpu = profile.get("cpu", {})
    print(f"  CPU:       {cpu.get('model', 'unknown')} ({cpu.get('cores', '?')} cores)")
    mem = profile.get("memory", {})
    print(f"  RAM:       {mem.get('total_gb', '?')} GB total, {mem.get('available_gb', '?')} GB available")
    for gpu in profile.get("gpu", []):
        print(f"  GPU:       {gpu['vendor']} {gpu['model']}")
    disk = profile.get("disk", {})
    if disk:
        print(f"  Disk:      {disk.get('total_gb', '?')} GB total, {disk.get('free_gb', '?')} GB free ({disk.get('used_pct', '?')}% used)")
    print(f"\n\033[36mSuggested model:\033[0m {suggest_model(profile)}")


def ai_config_cmd(args):
    c = cfg.load_config()
    ai = c.setdefault("ai", {})
    if args.key is None:
        print(json.dumps(ai, indent=2))
    elif args.value is not None:
        keys = args.key.split(".")
        target = ai
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        target[keys[-1]] = _coerce_value(args.value)
        cfg.save_config(c)
        print(f"Set ai.{args.key} = {json.dumps(target[keys[-1]])}")
    else:
        keys = args.key.split(".")
        target = ai
        for k in keys[:-1]:
            if k not in target:
                print(f"Key not found: {args.key}")
                return
            target = target[k]
        if keys[-1] in target:
            del target[keys[-1]]
            cfg.save_config(c)
            print(f"Unset ai.{args.key}")
        else:
            print(f"Key not found: {args.key}")


def _coerce_value(val):
    if val.lower() in ("true", "yes"):
        return True
    if val.lower() in ("false", "no"):
        return False
    if val.isdigit():
        return int(val)
    try:
        return float(val)
    except ValueError:
        return val


def setup_ollama(model=None):
    log = []
    has_ollama = check_ollama()
    result = {"ollama_installed": has_ollama}
    if not has_ollama:
        log.append("Ollama not found. Attempting install...")
        try:
            subprocess.run(
                ["curl", "-fsSL", "https://ollama.com/install.sh"],
                capture_output=True, text=True, timeout=30,
            )
            install_sh = subprocess.run(
                ["curl", "-fsSL", "https://ollama.com/install.sh"],
                capture_output=True, text=True, timeout=30,
            )
            if install_sh.returncode == 0:
                install_result = subprocess.run(
                    ["sh"], input=install_sh.stdout, capture_output=True, text=True, timeout=120,
                )
                if install_result.returncode != 0:
                    return {"error": f"Ollama install failed: {install_result.stderr.strip()}"}
                has_ollama = True
                result["ollama_installed"] = True
                log.append("Ollama installed successfully")
            else:
                return {"error": "Failed to download Ollama install script"}
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return {"error": f"Ollama install failed: {e}"}
    else:
        log.append("Ollama already installed")

    if not model:
        model = suggest_model(detect_hardware())
    log.append(f"Pulling model: {model}")
    result["model_pulled"] = model
    result["log"] = log
    return result


def benchmark_model(model=None, prompt="Hello"):
    if not check_ollama():
        return {"error": "Ollama not installed. Run 'ws ai setup' first."}
    if not model:
        model = "phi-4-mini:3.8b"
    import time
    start = time.time()
    try:
        out = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True, text=True, timeout=60,
        )
        elapsed = time.time() - start
        if out.returncode != 0:
            return {"error": f"Ollama inference failed: {out.stderr.strip()}"}
        response = out.stdout.strip()
        latency_ms = round(elapsed * 1000)
        tokens_per_sec = round(len(response.split()) / elapsed, 1) if elapsed > 0 else 0
        return {
            "model": model,
            "prompt": prompt,
            "response": response[:500],
            "response_length": len(response),
            "latency_ms": latency_ms,
            "tokens_per_sec": tokens_per_sec,
        }
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"error": f"Benchmark failed: {e}"}


_INTENT_MAP = {
    "status": ["status", "state", "what's going on", "what is going on", "show me", "dirty", "behind", "ahead"],
    "scan": ["scan", "discover", "find new", "new repos"],
    "health": ["health", "environment", "check tools", "dev environment"],
    "doctor": ["doctor", "diagnose", "issues", "problems", "what's wrong"],
    "feature_list": ["features", "feature list", "active features"],
    "log": ["log", "sessions", "history", "recent"],
    "help": ["help", "commands", "what can you do", "usage"],
}


def resolve_intent(query):
    q = query.lower().strip()
    for intent, patterns in _INTENT_MAP.items():
        for p in patterns:
            if p in q:
                return intent
    return None


_INTENT_COMMANDS = {
    "status": "ws status",
    "scan": "ws scan",
    "health": "ws health",
    "doctor": "ws doctor",
    "feature_list": "ws feature list",
    "log": "ws log",
    "help": "ws --help",
}


def exec_nl(query, dry_run=False):
    intent = resolve_intent(query)
    if not intent:
        return {"error": f"Could not understand query: {query!r}"}
    command = _INTENT_COMMANDS[intent]
    if dry_run:
        return {"intent": intent, "command": command}
    try:
        out = subprocess.run(command.split(), capture_output=True, text=True, timeout=30)
        output = out.stdout.strip()
        if out.returncode != 0:
            output = out.stderr.strip() or output
        return {"intent": intent, "command": command, "output": output}
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"error": f"Execution failed: {e}"}