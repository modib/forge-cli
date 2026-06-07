import json
import os
import re


from . import config as cfg

DEPS_FILE = os.path.join(cfg.WORKSPACE_DIR, "deps.json")

try:
    import tomllib
except ImportError:
    tomllib = None


def _load_deps_cache():
    if not os.path.exists(DEPS_FILE):
        return {}
    try:
        with open(DEPS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_deps_cache(cache):
    cfg.ensure_dir(cfg.WORKSPACE_DIR)
    with open(DEPS_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def _parse_name(n):
    if n.startswith("@"):
        return n
    return n.lower()


def parse_npm(path):
    """Parse package-lock.json, return list of {name, version, ecosystem}."""
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        return []
    deps = []
    for section in ("packages", "dependencies"):
        pkgs = data.get(section, {})
        for pkg_name, info in pkgs.items():
            if pkg_name == "":
                continue
            name = pkg_name.split("node_modules/")[-1] if "node_modules/" in pkg_name else pkg_name
            version = info.get("version", "")
            if name and version:
                deps.append({"name": _parse_name(name), "version": version.lstrip("^~"), "ecosystem": "npm"})
    return deps


def parse_cargo(path):
    """Parse Cargo.lock, return list of {name, version, ecosystem}."""
    if tomllib is None:
        return []
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, ValueError):
        return []
    deps = []
    for pkg in data.get("package", []):
        name = pkg.get("name", "")
        version = pkg.get("version", "")
        if name and version:
            deps.append({"name": _parse_name(name), "version": version, "ecosystem": "cargo"})
    return deps


def parse_pyproject(path):
    """Parse pyproject.toml for PEP 621 project.dependencies."""
    if tomllib is None:
        return []
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, ValueError):
        return []
    deps = []
    project = data.get("project", {})
    for dep_str in project.get("dependencies", []):
        m = re.match(r"^([a-zA-Z0-9_.-]+)\s*([><=!~]+.*)?", dep_str)
        if m:
            name = m.group(1)
            spec = m.group(2) or ""
            version = spec.lstrip(">=<~!=") if spec else ""
            deps.append({"name": _parse_name(name), "version": version, "ecosystem": "pypi", "requirement": dep_str})
    for group_name, group_deps in project.get("optional-dependencies", {}).items():
        for dep_str in group_deps:
            m = re.match(r"^([a-zA-Z0-9_.-]+)\s*([><=!~]+.*)?", dep_str)
            if m:
                name = m.group(1)
                spec = m.group(2) or ""
                version = spec.lstrip(">=<~!=") if spec else ""
                deps.append({
                    "name": _parse_name(name),
                    "version": version,
                    "ecosystem": "pypi",
                    "requirement": dep_str,
                    "optional": True,
                    "group": group_name,
                })
    return deps


def parse_requirements(path):
    """Parse requirements.txt, return list of {name, version, ecosystem}."""
    deps = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                m = re.match(r"^([a-zA-Z0-9_.-]+)\s*([><=!~]+.*)?", line)
                if m:
                    name = m.group(1)
                    spec = m.group(2) or ""
                    version = spec.lstrip(">=<~!=") if spec else ""
                    deps.append({
                        "name": _parse_name(name),
                        "version": version,
                        "ecosystem": "pypi",
                        "requirement": line,
                    })
    except (OSError, UnicodeDecodeError):
        pass
    return deps


def parse_gosum(path):
    deps = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    ver = parts[1]
                    if ver.startswith("v") and name:
                        deps[f"{name}@{ver}"] = {"name": name, "version": ver, "ecosystem": "go"}
    except (OSError, UnicodeDecodeError):
        pass
    return list(deps.values())


def parse_gemfile(path):
    """Parse Gemfile.lock, return list of {name, version, ecosystem}."""
    deps = []
    in_specs = False
    try:
        with open(path) as f:
            for line in f:
                stripped = line.strip()
                if stripped == "GEM":
                    in_specs = False
                if stripped == "specs:":
                    in_specs = True
                    continue
                if in_specs and stripped and not stripped.startswith("specs:") and not stripped.startswith("GEM"):
                    m = re.match(r"^\s+(\S+)\s+\((\S+)\)", line)
                    if m:
                        name = m.group(1)
                        version = m.group(2)
                        deps.append({"name": _parse_name(name), "version": version, "ecosystem": "rubygems"})
                if stripped.startswith("PLATFORMS") or stripped.startswith("DEPENDENCIES"):
                    in_specs = False
    except (OSError, UnicodeDecodeError):
        pass
    return deps


PARSERS = {
    "package-lock.json": parse_npm,
    "Cargo.lock": parse_cargo,
    "pyproject.toml": parse_pyproject,
    "requirements.txt": parse_requirements,
    "go.sum": parse_gosum,
    "Gemfile.lock": parse_gemfile,
}


def _find_lockfiles(repo_path):
    files = {}
    for fname in PARSERS:
        fpath = os.path.join(repo_path, fname)
        if os.path.isfile(fpath):
            files[fname] = fpath
    if not files.get("pyproject.toml") and os.path.isfile(os.path.join(repo_path, "requirements.txt")):
        pass
    return files


def parse_repo_deps(repo_path):
    all_deps = {}
    seen = set()
    for fname, fpath in _find_lockfiles(repo_path).items():
        parser = PARSERS[fname]
        deps = parser(fpath)
        for dep in deps:
            key = f"{dep['ecosystem']}:{dep['name']}"
            if key not in seen:
                seen.add(key)
                all_deps[key] = dep
    return list(all_deps.values())


def update_deps_for_repo(repo_name, repo_path):
    deps = parse_repo_deps(repo_path)
    cache = _load_deps_cache()
    cache[repo_name] = deps
    _save_deps_cache(cache)
    return deps


def get_deps(repo_name=None):
    cache = _load_deps_cache()
    if repo_name:
        return cache.get(repo_name, [])
    return cache


def list_deps(repo_name=None, ecosystem=None):
    cache = get_deps(repo_name)
    if repo_name:
        deps = cache
    else:
        deps = [d for repo in cache.values() for d in repo]
    if ecosystem:
        deps = [d for d in deps if d["ecosystem"] == ecosystem]
    return sorted(deps, key=lambda d: (d["ecosystem"], d["name"]))


def deps_count(repo_name=None):
    cache = get_deps(repo_name)
    if repo_name:
        return len(cache)
    return sum(len(d) for d in cache.values())
