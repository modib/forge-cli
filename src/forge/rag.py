import json
import os
import ssl
import subprocess
import urllib.error
import urllib.request

from . import config as cfg
from . import cve as forge_cve
from . import deps as forge_deps

OLLAMA_BASE = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
EMBEDDING_MODEL = "nomic-embed-text"
INDEX_FILE = os.path.join(cfg.WORKSPACE_DIR, "index.json")


def _ensure_embedding_model():
    try:
        out = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and EMBEDDING_MODEL in out.stdout:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    print(f"\r\033[36m▸\033[0m Pulling embedding model ({EMBEDDING_MODEL})...", end="", flush=True)
    try:
        pull = subprocess.run(["ollama", "pull", EMBEDDING_MODEL], capture_output=True, text=True, timeout=120)
        print("\r" + " " * 60, end="\r", flush=True)
        return pull.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("\r" + " " * 60, end="\r", flush=True)
        return False


def _ollama_embed(text):
    data = json.dumps({"model": EMBEDDING_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/embeddings",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            result = json.loads(resp.read())
        return result.get("embedding", [])
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return []


def _load_index():
    if not os.path.exists(INDEX_FILE):
        return None
    try:
        with open(INDEX_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def _save_index(index):
    cfg.ensure_dir(cfg.WORKSPACE_DIR)
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)


def _cosine_sim(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0
    return dot / (na * nb)


def _chunk_repo(repo):
    chunks = []
    for rp in ("README.md", "readme.md", "Readme.md"):
        rp_full = os.path.join(repo["path"], rp)
        if os.path.isfile(rp_full):
            try:
                with open(rp_full) as f:
                    readme_text = f.read(2000)
            except (OSError, UnicodeDecodeError):
                readme_text = ""
            if readme_text:
                chunks.append({
                    "id": f"readme:{repo['name']}",
                    "text": readme_text,
                    "metadata": {"type": "readme", "repo": repo["name"]},
                })
            break

    deps = forge_deps.list_deps(repo_name=repo["name"])
    if deps:
        dep_lines = [f"{d['ecosystem']}:{d['name']}@{d['version'] or '*'}" for d in deps[:30]]
        chunks.append({
            "id": f"deps:{repo['name']}",
            "text": f"Repository {repo['name']} depends on: {', '.join(dep_lines)}",
            "metadata": {"type": "deps", "repo": repo["name"]},
        })

    return chunks


def _chunk_cves():
    cves = forge_cve.list_cves()
    if not cves:
        return []
    by_pkg = {}
    for v in cves:
        key = f"{v['ecosystem']}:{v['package']}@{v['version']}"
        if key not in by_pkg:
            by_pkg[key] = []
        by_pkg[key].append(v["id"])
    chunks = []
    for pkg_key, vuln_ids in by_pkg.items():
        text = f"{pkg_key} has {len(vuln_ids)} known vulnerabilities: {', '.join(vuln_ids[:10])}"
        chunks.append({
            "id": f"cve:{pkg_key}",
            "text": text,
            "metadata": {"type": "cve", "ecosystem": pkg_key.split(":")[0], "package": pkg_key.split(":")[1].split("@")[0]},
        })
    return chunks


def build_index():
    if not _ensure_embedding_model():
        print("\033[31mFailed to load embedding model. Is Ollama running?\033[0m")
        return 0

    c = cfg.load_config()
    repos = c.get("repos", [])
    chunks = []

    for repo in repos:
        chunks.extend(_chunk_repo(repo))

    chunks.extend(_chunk_cves())

    repo_names = [r["name"] for r in repos]
    chunks.append({
        "id": "workspace:overview",
        "text": f"Workspace has {len(repos)} repositories: {', '.join(repo_names)}" if repo_names else "Workspace has no repositories registered yet.",
        "metadata": {"type": "workspace"},
    })

    total = len(chunks)
    print(f"Indexing {total} chunks...")

    for i, chunk in enumerate(chunks):
        embedding = _ollama_embed(chunk["text"])
        if embedding:
            chunk["embedding"] = embedding
        if (i + 1) % 5 == 0:
            print(f"  {i + 1}/{total} chunks embedded", end="\r", flush=True)

    print(f"  {total}/{total} chunks embedded" + " " * 10)

    indexed_chunks = [c for c in chunks if c.get("embedding")]
    _save_index({"model": EMBEDDING_MODEL, "chunks": indexed_chunks})

    skipped = total - len(indexed_chunks)
    print(f"\033[32mIndexed {len(indexed_chunks)} chunks\033[0m" + (f" ({skipped} skipped)" if skipped else ""))
    return len(indexed_chunks)


def search(query, k=5):
    index = _load_index()
    if not index or not index.get("chunks"):
        return []
    q_emb = _ollama_embed(query)
    if not q_emb:
        return []
    scored = []
    for chunk in index["chunks"]:
        emb = chunk.get("embedding", [])
        if not emb:
            continue
        sim = _cosine_sim(q_emb, emb)
        scored.append((sim, chunk))
    scored.sort(key=lambda x: -x[0])
    return scored[:k]


def ask(query):
    import shutil
    if not shutil.which("ollama"):
        return "Ollama is not installed. Run `forge ai setup` first."
    if not _ensure_embedding_model():
        return "Failed to load embedding model."

    index = _load_index()
    if not index:
        print("\033[90mNo workspace index found. Building one now...\033[0m")
        build_index()
        index = _load_index()

    results = search(query)
    context_parts = []
    for sim, chunk in results:
        meta = chunk.get("metadata", {})
        tag = meta.get("repo", meta.get("package", meta.get("type", "?")))
        source = f"[{meta.get('type', '?')}: {tag}]"
        context_parts.append(f"--- {source} ---\n{chunk['text']}")

    context = "\n\n".join(context_parts) if context_parts else "No relevant context found in workspace index."

    prompt = f"""You are a workspace intelligence assistant. Answer based ONLY on the context below.
If the context doesn't contain enough information, say so and suggest a command the user could run.

Context:
{context}

Question: {query}

Answer concisely:"""

    data = json.dumps({"model": "gemma4:e2b", "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    ctx = ssl.create_default_context()
    print("\033[90mThinking...\033[0m", end="", flush=True)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
            result = json.loads(resp.read())
        answer = result.get("response", "").strip()
        print("\r" + " " * 12, end="\r", flush=True)
        return answer
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        print("\r" + " " * 12, end="\r", flush=True)
        return f"Failed to get answer: {e}"