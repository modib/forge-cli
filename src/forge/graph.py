import os
from collections import defaultdict
from . import config as cfg
from . import git


def _parse_log_output(stdout):
    file_commits = defaultdict(set)
    blocks = stdout.split("---\n")
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")
        commit_hash = lines[0].strip() if lines else ""
        if not commit_hash:
            continue
        for f in lines[1:]:
            f = f.strip()
            if f and not f.startswith("---"):
                file_commits[f].add(commit_hash)
    return file_commits


def co_change_graph(path, depth=50):
    if not os.path.exists(path):
        return {"error": f"Path not found: {path}"}
    if not git.is_git_repo(path):
        return {"error": f"Not a git repository: {path}"}

    stdout, _, rc = git.run_git(path, "log", f"-{depth}", "--format=---%n%H", "--name-only")
    if rc != 0 or not stdout.strip():
        return {"nodes": [], "edges": []}

    file_commits = _parse_log_output(stdout)
    if not file_commits:
        return {"nodes": [], "edges": []}

    all_commits = set()
    for commits in file_commits.values():
        all_commits.update(commits)

    edge_weights = defaultdict(int)
    for commit_hash in all_commits:
        files_in_commit = [f for f, commits in file_commits.items() if commit_hash in commits]
        for i in range(len(files_in_commit)):
            for j in range(i + 1, len(files_in_commit)):
                a, b = sorted([files_in_commit[i], files_in_commit[j]])
                edge_weights[(a, b)] += 1

    nodes = [{"id": f, "commits": len(commits_set)} for f, commits_set in sorted(file_commits.items())]
    edges = [{"source": a, "target": b, "weight": w} for (a, b), w in sorted(edge_weights.items(), key=lambda x: -x[1])]

    return {"nodes": nodes, "edges": edges}


def branch_graph(path):
    if not os.path.exists(path):
        return {"error": f"Path not found: {path}"}
    if not git.is_git_repo(path):
        return {"error": f"Not a git repository: {path}"}

    stdout, _, rc = git.run_git(path, "branch", "-a")
    if rc != 0:
        return {"error": "Failed to list branches"}

    branches = [b.strip().replace("* ", "").strip() for b in stdout.split("\n") if b.strip()]

    current_branch, _, _ = git.run_git(path, "rev-parse", "--abbrev-ref", "HEAD")

    history, _, _ = git.run_git(path, "log", "--all", "--oneline", "--graph", "--decorate", "-30")

    return {
        "branches": branches,
        "current": current_branch if current_branch != "HEAD" else "detached",
        "history": history,
    }


def generate_graph(name, graph_type="co-change", output_format="json", depth=50):
    c = cfg.load_config()
    repo = cfg.repo_by_name(c, name)
    if not repo:
        return {"error": f"Repo not found: {name}"}

    path = repo["path"]
    if graph_type == "co-change":
        result = co_change_graph(path, depth=depth)
    elif graph_type == "branches":
        result = branch_graph(path)
    else:
        return {"error": f"Unknown graph type: {graph_type}"}

    result["repo"] = name
    return result


def cross_repo_impact(dirty_repos_and_paths, depth=30):
    impacts = []
    repo_paths = list(dirty_repos_and_paths.items())
    for i in range(len(repo_paths)):
        for j in range(i + 1, len(repo_paths)):
            name_a, path_a = repo_paths[i]
            name_b, path_b = repo_paths[j]
            if not os.path.exists(path_a) or not os.path.exists(path_b):
                continue
            if not git.is_git_repo(path_a) or not git.is_git_repo(path_b):
                continue

            stdout_a, _, rc_a = git.run_git(path_a, "log", f"-{depth}", "--format=---%n%H", "--name-only")
            stdout_b, _, rc_b = git.run_git(path_b, "log", f"-{depth}", "--format=---%n%H", "--name-only")
            if rc_a != 0 or rc_b != 0:
                continue

            files_a = set()
            for block in stdout_a.split("---\n"):
                for line in block.split("\n")[1:]:
                    line = line.strip()
                    if line and not line.startswith("---"):
                        files_a.add(line)

            files_b = set()
            for block in stdout_b.split("---\n"):
                for line in block.split("\n")[1:]:
                    line = line.strip()
                    if line and not line.startswith("---"):
                        files_b.add(line)

            common = files_a & files_b
            if common:
                impacts.append({
                    "repo_a": name_a,
                    "repo_b": name_b,
                    "shared_files": sorted(common),
                    "shared_count": len(common),
                })

    return impacts
