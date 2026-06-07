import json
import os
import platform
import re
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
    profile["apple_silicon"] = _is_apple_silicon()
    profile["mlx_available"] = _check_mlx_available()
    profile["recommended_backend"] = _recommend_backend(profile)
    return profile


def _is_apple_silicon():
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def _check_mlx_available():
    try:
        import mlx  # noqa: F401
        return True
    except ImportError:
        return False


def _detect_cpu():
    info = {"cores": os.cpu_count() or 0}
    if _is_apple_silicon():
        try:
            out = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True, timeout=5)
            if out.returncode == 0 and out.stdout.strip():
                info["model"] = out.stdout.strip()
                return info
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        info["model"] = "Apple Silicon"
        return info
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
    if _is_apple_silicon():
        try:
            out = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5)
            if out.returncode == 0 and out.stdout.strip():
                total_bytes = int(out.stdout.strip())
                info["total_gb"] = round(total_bytes / (1024**3), 1)
                return info
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass
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
    if _is_apple_silicon():
        try:
            out = subprocess.run(["system_profiler", "SPDisplaysDataType"], capture_output=True, text=True, timeout=10)
            if out.returncode == 0:
                for line in out.stdout.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("Chipset Model:"):
                        gpus.append({"vendor": "apple", "model": stripped.split(":", 1)[1].strip()})
                    elif stripped.startswith("VRAM ("):
                        gpus.append({"vendor": "apple", "memory": stripped.split(":", 1)[1].strip()})
                if gpus:
                    return gpus
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        gpus.append({"vendor": "apple", "model": "Apple Silicon (unified)"})
        return gpus
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


def _recommend_backend(profile):
    if profile.get("apple_silicon") and profile.get("memory", {}).get("total_gb", 0) >= 8:
        return "mlx"
    return "ollama"


def suggest_model(profile, backend=None):
    mem = profile.get("memory", {}).get("total_gb", 0)
    apple_silicon = profile.get("apple_silicon", False)
    if backend is None:
        backend = _recommend_backend(profile)
    if apple_silicon and backend == "mlx":
        if mem >= 16:
            return "Qwen2.5-Coder-7B-Instruct"
        if mem >= 8:
            return "Qwen2.5-Coder-7B-Instruct"
        return "Qwen2.5-Coder-1.5B-Instruct"
    if mem >= 16:
        return "gemma4:e4b"
    if mem >= 8:
        return "gemma4:e2b"
    return "gemma4:e2b"


def check_ollama():
    return bool(shutil.which("ollama"))


def detect_and_print(args):
    profile = detect_hardware()
    if args.json:
        print(json.dumps(profile, indent=2))
        return
    backend = getattr(args, "backend", None) or profile["recommended_backend"]
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
    apple = profile.get("apple_silicon", False)
    mlx = profile.get("mlx_available", False)
    if apple:
        check_mark = "\033[32m✓\033[0m"
        print(f"  Apple Silicon: {check_mark}")
        mlx_status = check_mark if mlx else "\033[33mnot installed\033[0m"
        print(f"  MLX:          {mlx_status}")
    print(f"  Recommended backend: \033[36m{profile['recommended_backend']}\033[0m")
    print(f"\n\033[36mSuggested model\033[0m (--backend {backend}): {suggest_model(profile, backend)}")


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


def setup(backend=None, model=None):
    profile = detect_hardware()
    if backend is None:
        backend = profile["recommended_backend"]
    if backend == "mlx":
        return setup_mlx(model=model, profile=profile)
    return setup_ollama(model=model, profile=profile)


def setup_ollama(model=None, profile=None):
    if profile is None:
        profile = detect_hardware()
    log = []
    has_ollama = check_ollama()
    result = {"backend": "ollama", "ollama_installed": has_ollama}
    if not has_ollama:
        log.append("Ollama not found. Attempting install...")
        try:
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
        model = suggest_model(profile, backend="ollama")
    log.append(f"Pulling model: {model}...")
    print(f"\r\033[36m▸\033[0m Pulling {model} (this may take a few minutes)...", end="", flush=True)
    try:
        pull = subprocess.run(["ollama", "pull", model], capture_output=True, text=True, timeout=300)
        print("\r" + " " * 60, end="", flush=True)
        if pull.returncode != 0:
            return {"error": f"Failed to pull model {model}: {pull.stderr.strip()}"}
        print("\033[32m✓ Model download complete\033[0m")
        log.append(f"Model {model} downloaded")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"error": f"Model pull timed out: {e}"}
    result["model"] = model
    result["log"] = log
    return result


def setup_mlx(model=None, profile=None):
    if profile is None:
        profile = detect_hardware()
    log = []
    result = {"backend": "mlx"}
    if not profile.get("apple_silicon"):
        return {"error": "MLX requires Apple Silicon (M1-M4). Use --backend ollama instead."}
    has_mlx = _check_mlx_available()
    if not has_mlx:
        log.append("Installing MLX...")
        try:
            out = subprocess.run(
                [sys.executable, "-m", "pip", "install", "mlx", "mlx-lm"],
                capture_output=True, text=True, timeout=120,
            )
            if out.returncode != 0:
                return {"error": f"MLX install failed: {out.stderr.strip()}"}
            has_mlx = True
            log.append("MLX installed successfully")
        except subprocess.TimeoutExpired as e:
            return {"error": f"MLX install timed out: {e}"}
    else:
        log.append("MLX already installed")
    if not model:
        model = suggest_model(profile, backend="mlx")
    log.append(f"Suggested model: {model}")
    result["model"] = model
    result["mlx_installed"] = has_mlx
    result["log"] = log
    return result


def benchmark_model(model=None, prompt="Hello", backend=None):
    profile = detect_hardware()
    if backend is None:
        backend = profile["recommended_backend"]
    if backend == "mlx":
        return _benchmark_mlx(model=model, prompt=prompt)
    return _benchmark_ollama(model=model, prompt=prompt)


def _benchmark_ollama(model=None, prompt="Hello"):
    if not check_ollama():
        return {"error": "Ollama not installed. Run 'forge ai setup' first."}
    if not model:
        model = "gemma4:e2b"
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
            "backend": "ollama",
            "model": model,
            "prompt": prompt,
            "response": response[:500],
            "response_length": len(response),
            "latency_ms": latency_ms,
            "tokens_per_sec": tokens_per_sec,
        }
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"error": f"Benchmark failed: {e}"}


def _benchmark_mlx(model=None, prompt="Hello"):
    if not _check_mlx_available():
        return {"error": "MLX not installed. Run 'forge ai setup --backend mlx' first."}
    if not model:
        model = "Qwen2.5-Coder-1.5B-Instruct"
    if not _is_apple_silicon():
        return {"error": "MLX requires Apple Silicon hardware"}
    try:
        from mlx_lm import load, generate
        import time
        start = time.time()
        model_obj, tokenizer = load(f"mlx-community/{model}")
        response = generate(model_obj, tokenizer, prompt=prompt, max_tokens=128, verbose=False)
        elapsed = time.time() - start
        latency_ms = round(elapsed * 1000)
        tokens_per_sec = round(len(response.split()) / elapsed, 1) if elapsed > 0 else 0
        return {
            "backend": "mlx",
            "model": model,
            "prompt": prompt,
            "response": response[:500],
            "response_length": len(response),
            "latency_ms": latency_ms,
            "tokens_per_sec": tokens_per_sec,
        }
    except Exception as e:
        return {"error": f"MLX benchmark failed: {e}"}


_INTENT_MAP = {
    "status": ["status", "state", "what's going on", "what is going on", "show me", "dirty", "behind", "ahead"],
    "scan": ["scan", "discover", "find new", "new repos", "vulnerable", "security", "audit"],
    "health": ["health", "environment", "check tools", "dev environment"],
    "doctor": ["doctor", "diagnose", "issues", "problems", "what's wrong"],
    "feature_list": ["features", "feature list", "active features"],
    "log": ["log", "sessions", "history", "recent"],
    "help": ["help", "commands", "what can you do", "usage"],
}

_INTENT_COMMANDS = {
    "status": "forge status",
    "scan": "forge scan",
    "health": "forge health",
    "doctor": "forge doctor",
    "feature_list": "forge feature list",
    "log": "forge log",
    "help": "forge --help",
}

_EXEC_PROMPT = """You are a workspace command router. Given a natural language query, determine which workspace command the user wants.

Available intents:
- status: Check workspace/repo status (keywords: dirty, behind, ahead, state, what's going on)
- scan: Discover new repos, check for vulnerable libraries or security issues
- health: Check dev environment tools (brew, ollama, gh, python)
- doctor: Diagnose workspace issues (missing repos, stale worktrees)
- feature_list: List active feature branches
- log: View agent session history
- help: Show help and available commands

Respond with ONLY a JSON object: {{"intent": "<intent_name>", "confidence": 0.95}}
If the query does not match any intent, respond with: {{"intent": "unknown", "confidence": 0}}

Query: {query}"""


def _parse_json_response(response):
    match = re.search(r"\{[^}]*\}", response)
    if match:
        try:
            data = json.loads(match.group())
            intent = data.get("intent", "unknown")
            if intent in _INTENT_COMMANDS:
                return intent
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def check_model_ready(backend=None, model=None):
    profile = detect_hardware()
    if backend is None:
        backend = profile["recommended_backend"]
    if backend == "mlx":
        if not profile.get("apple_silicon"):
            return {"ready": False, "error": "MLX requires Apple Silicon"}
        if not _check_mlx_available():
            return {"ready": False, "error": "MLX not installed. Run 'forge ai setup --backend mlx'"}
        return {"ready": True, "backend": "mlx", "model": model or suggest_model(profile, "mlx")}
    if not check_ollama():
        return {"ready": False, "error": "Ollama not installed. Run 'forge ai setup'"}
    suggested = model or suggest_model(profile, "ollama")
    try:
        out = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and suggested in out.stdout:
            return {"ready": True, "backend": "ollama", "model": suggested}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return {"ready": True, "backend": "ollama", "model": suggested, "note": "Model not pulled yet — will download on first use"}


def _get_github_token():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _resolve_with_github_models(query):
    token = _get_github_token()
    if not token:
        return None
    prompt = _EXEC_PROMPT.format(query=query)
    import urllib.request
    req = urllib.request.Request(
        "https://models.inference.ai.azure.com/chat/completions",
        data=json.dumps({
            "model": "Phi-4-mini-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 50,
        }).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"]
            result = _parse_json_response(content)
            if result:
                return result
    except Exception as e:
        print(f"\033[90mforge: GitHub Models API error: {e}\033[0m", file=sys.stderr)
    return None


def _ensure_ollama_model(model, timeout=300):
    out = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
    if out.returncode == 0 and model in out.stdout:
        return True
    print(f"\033[90mforge: downloading {model} (this may take a minute)...\033[0m", file=sys.stderr)
    pull = subprocess.run(["ollama", "pull", model], capture_output=True, text=True, timeout=timeout)
    if pull.returncode != 0:
        print(f"\033[90mforge: download failed: {pull.stderr.strip()}\033[0m", file=sys.stderr)
        return False
    print(f"\033[90mforge: {model} ready\033[0m", file=sys.stderr)
    return True


def _resolve_with_ollama(query, model=None):
    if not check_ollama():
        return None
    profile = detect_hardware()
    if not model:
        model = suggest_model(profile, "ollama")
    if not _ensure_ollama_model(model):
        return None
    prompt = _EXEC_PROMPT.format(query=query)
    try:
        out = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True, text=True, timeout=300,
        )
        if out.returncode != 0:
            return None
        return _parse_json_response(out.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _resolve_with_mlx(query, model=None):
    if not _is_apple_silicon() or not _check_mlx_available():
        return None
    profile = detect_hardware()
    if not model:
        model = suggest_model(profile, "mlx")
    prompt = _EXEC_PROMPT.format(query=query)
    try:
        from mlx_lm import load, generate
        print(f"\033[90mforge: loading {model}...\033[0m", file=sys.stderr)
        model_obj, tokenizer = load(f"mlx-community/{model}")
        response = generate(model_obj, tokenizer, prompt=prompt, max_tokens=128, verbose=False)
        return _parse_json_response(response)
    except Exception:
        return None


def _resolve_intent_keywords(query):
    q = query.lower().strip()
    for intent, patterns in _INTENT_MAP.items():
        for p in patterns:
            if p in q:
                return intent
    return None


def _run_command(intent, dry_run=False, resolved_by=""):
    command = _INTENT_COMMANDS[intent]
    if dry_run:
        return {"intent": intent, "command": command, "resolved_by": resolved_by or "keyword"}
    try:
        out = subprocess.run(command.split(), capture_output=True, text=True, timeout=30)
        output = out.stdout.strip()
        if out.returncode != 0:
            output = out.stderr.strip() or output
        return {"intent": intent, "command": command, "output": output, "resolved_by": resolved_by or "keyword"}
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"error": f"Execution failed: {e}"}


def exec_nl(query, dry_run=False):
    intent = _resolve_intent_keywords(query)
    if intent:
        return _run_command(intent, dry_run, resolved_by="keyword")

    intent = _resolve_with_github_models(query)
    if intent:
        return _run_command(intent, dry_run, resolved_by="GitHub Models")

    profile = detect_hardware()
    backend = profile["recommended_backend"]
    ready = check_model_ready(backend=backend)
    if not ready.get("ready"):
        hint = ready.get("error", "no model backend available")
        return {"error": f"I couldn't understand that query. Try something like 'show me dirty repos'. ({hint})"}
    model = ready["model"]
    note = ready.get("note", "")
    if note:
        print(f"\033[90mforge: {note}\033[0m", file=sys.stderr)
    if backend == "mlx":
        intent = _resolve_with_mlx(query, model)
    else:
        intent = _resolve_with_ollama(query, model)
    if intent:
        return _run_command(intent, dry_run, resolved_by=f"local model ({backend})")
    return {"error": "I couldn't understand that query. Try something like 'show me dirty repos' or 'forge status'."}