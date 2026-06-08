import json
import os
import ssl
import urllib.error
import urllib.request

from . import config as cfg
from . import deps

CVE_FILE = os.path.join(cfg.WORKSPACE_DIR, "cve.json")

OSV_QUERY_URL = "https://api.osv.dev/v1/query"
OSV_VULN_URL = "https://api.osv.dev/v1/vulns/"

ECOSYSTEM_MAP = {
    "npm": "npm",
    "cargo": "crates.io",
    "pypi": "PyPI",
    "go": "Go",
    "rubygems": "RubyGems",
}


def _load_cache():
    if not os.path.exists(CVE_FILE):
        return {}
    try:
        with open(CVE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_cache(cache):
    os.makedirs(os.path.dirname(CVE_FILE), exist_ok=True)
    with open(CVE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def _osv_ecosystem(dep):
    return ECOSYSTEM_MAP.get(dep.get("ecosystem", ""), "")


def _dep_key(dep):
    eco = _osv_ecosystem(dep)
    if not eco or not dep.get("name") or not dep.get("version"):
        return None
    return f"{eco}:{dep['name']}@{dep['version']}"


def _query_osv(package_name, ecosystem, version):
    payload = json.dumps({
        "package": {"name": package_name, "ecosystem": ecosystem},
        "version": version,
    }).encode()
    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        OSV_QUERY_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            result = json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return []
    vulns = result.get("vulns", [])
    out = []
    for v in vulns:
        out.append({
            "id": v.get("id", ""),
            "modified": v.get("modified", ""),
            "summary": "",
            "aliases": [],
            "cvss_score": None,
        })
    return out


def _parse_fix_versions(data):
    fixes = []
    for affected in data.get("affected", []):
        pkg = affected.get("package", {})
        pkg_name = pkg.get("name", "")
        ecosystem = pkg.get("ecosystem", "")
        for rng in affected.get("ranges", []):
            if rng.get("type") != "ECOSYSTEM":
                continue
            introduced = None
            fixed = None
            for event in rng.get("events", []):
                if "introduced" in event:
                    introduced = event["introduced"]
                if "fixed" in event:
                    fixed = event["fixed"]
            fixes.append({
                "package": pkg_name,
                "ecosystem": ecosystem,
                "introduced": introduced or "0",
                "fixed": fixed or "unknown",
            })
    return fixes


def _fetch_vuln_detail(vuln_id):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(f"{OSV_VULN_URL}{vuln_id}")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return None
    summary = data.get("summary", "")
    aliases = data.get("aliases", [])
    cvss_score = None
    for ref in data.get("references", []):
        if ref.get("type") == "REPORT" and "cvss" in ref:
            try:
                cvss_score = float(ref["cvss"])
            except (ValueError, TypeError):
                pass
    if cvss_score is None:
        ds = data.get("database_specific", {})
        if isinstance(ds, dict):
            severity = ds.get("severity", "")
            if severity == "CRITICAL":
                cvss_score = 9.5
            elif severity == "HIGH":
                cvss_score = 7.5
            elif severity == "MODERATE":
                cvss_score = 5.0
            elif severity == "LOW":
                cvss_score = 2.5
    return {
        "id": vuln_id,
        "summary": summary,
        "aliases": aliases,
        "cvss_score": cvss_score,
        "fix_versions": _parse_fix_versions(data),
    }


def _find_lockfiles_for_dep(repo_path, dep):
    found = []
    for fname in deps.PARSERS:
        fpath = os.path.join(repo_path, fname)
        if os.path.isfile(fpath):
            found.append(fpath)
    return found


def fix_info(vuln_id):
    detail = _fetch_vuln_detail(vuln_id)
    if detail is None:
        return {"error": f"Could not fetch details for {vuln_id}"}
    cache = _load_cache()
    affected_repos = {}
    c = cfg.load_config()
    for repo in c.get("repos", []):
        repo_deps = deps.get_deps(repo_name=repo["name"])
        for dep in repo_deps:
            vulns = _vulns_for_dep(dep, cache)
            if not any(v["id"] == vuln_id for v in vulns):
                continue
            lockfiles = _find_lockfiles_for_dep(repo["path"], dep)
            fix_versions_for_dep = []
            for fix in detail.get("fix_versions", []):
                eco_map = {"npm": "npm", "cargo": "crates.io", "pypi": "PyPI", "go": "Go", "rubygems": "RubyGems"}
                mapped_eco = eco_map.get(dep["ecosystem"], "")
                if dep["name"] == fix["package"] and mapped_eco == fix["ecosystem"]:
                    fix_versions_for_dep.append(fix)
            if fix_versions_for_dep:
                affected_repos.setdefault(repo["name"], []).append({
                    "dep": dep,
                    "fix_versions": fix_versions_for_dep,
                    "lockfiles": lockfiles,
                })
    return {
        "vuln_id": vuln_id,
        "summary": detail.get("summary", ""),
        "cvss_score": detail.get("cvss_score"),
        "fix_versions": detail.get("fix_versions", []),
        "affected_repos": affected_repos,
    }


def _vulns_for_dep(dep, cache):
    key = _dep_key(dep)
    if not key:
        return []
    raw = cache.get(key, [])
    out = []
    for v in raw:
        detail = cache.get(f"_detail:{v['id']}", {})
        out.append({
            "id": v["id"],
            "summary": detail.get("summary", v.get("summary", "")),
            "aliases": detail.get("aliases", v.get("aliases", [])),
            "cvss_score": detail.get("cvss_score", v.get("cvss_score")),
            "package": dep["name"],
            "version": dep["version"],
            "ecosystem": dep["ecosystem"],
        })
    return out


def refresh():
    all_deps = deps.list_deps()
    cache = _load_cache()
    queried = 0
    fresh = 0
    for dep in all_deps:
        key = _dep_key(dep)
        if not key:
            continue
        if key in cache:
            continue
        vulns = _query_osv(dep["name"], _osv_ecosystem(dep), dep["version"])
        cache[key] = vulns
        queried += 1
        fresh += len(vulns)
    _save_cache(cache)
    total_cached = sum(
        len(v) for k, v in cache.items() if not k.startswith("_detail:")
    )
    return {"queried": queried, "vulns_found": fresh, "total_cached": total_cached}


def list_cves(repo_name=None, ecosystem=None, min_score=None):
    cache = _load_cache()
    all_deps = deps.list_deps(repo_name=repo_name)
    results = []
    for dep in all_deps:
        if ecosystem and dep["ecosystem"] != ecosystem:
            continue
        vulns = _vulns_for_dep(dep, cache)
        for v in vulns:
            if min_score is not None and (v["cvss_score"] is None or v["cvss_score"] < min_score):
                continue
            results.append(v)
    return sorted(results, key=lambda r: r["id"])


def describe(vuln_id, refresh_cache=False):
    cache = _load_cache()
    detail_key = f"_detail:{vuln_id}"
    if refresh_cache or detail_key not in cache:
        detail = _fetch_vuln_detail(vuln_id)
        if detail is None:
            return None
        cache[detail_key] = detail
        _save_cache(cache)
        return detail
    return cache.get(detail_key)


def report(repo_name=None, ecosystem=None, min_score=None):
    cves = list_cves(repo_name=repo_name, ecosystem=ecosystem, min_score=min_score)
    total = len(cves)
    by_severity = {"critical": 0, "high": 0, "moderate": 0, "low": 0, "unknown": 0}
    by_eco = {}
    by_package = {}
    for v in cves:
        score = v.get("cvss_score")
        if score is None:
            by_severity["unknown"] += 1
        elif score >= 9.0:
            by_severity["critical"] += 1
        elif score >= 7.0:
            by_severity["high"] += 1
        elif score >= 4.0:
            by_severity["moderate"] += 1
        else:
            by_severity["low"] += 1
        eco = v["ecosystem"]
        by_eco[eco] = by_eco.get(eco, 0) + 1
        pkg = v["package"]
        by_package[pkg] = by_package.get(pkg, 0) + 1
    top_packages = sorted(by_package.items(), key=lambda x: -x[1])[:10]
    return {
        "total": total,
        "by_severity": by_severity,
        "by_ecosystem": by_eco,
        "top_packages": top_packages,
    }
