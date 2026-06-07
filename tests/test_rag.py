import json
import os
from unittest.mock import MagicMock, patch
from forge import rag as forge_rag
from forge import deps as forge_deps


def _make_embedding(dim=4):
    import math
    return [1.0 / math.sqrt(dim)] * dim


class TestCosineSim:
    def test_identical(self):
        a = [1.0, 0.0, 0.0]
        assert forge_rag._cosine_sim(a, a) == 1.0

    def test_orthogonal(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert forge_rag._cosine_sim(a, b) == 0.0

    def test_opposite(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert forge_rag._cosine_sim(a, b) == -1.0

    def test_zero_vector(self):
        assert forge_rag._cosine_sim([0.0, 0.0], [1.0, 0.0]) == 0.0


class TestChunkRepo:
    def test_chunk_with_readme_and_deps(self, tmp_path):
        repo_path = tmp_path / "myapp"
        repo_path.mkdir()
        (repo_path / "README.md").write_text("My app is a web framework")
        repo = {"name": "myapp", "path": str(repo_path)}
        with patch.object(forge_deps, "list_deps", return_value=[
            {"name": "flask", "version": "2.0", "ecosystem": "pypi"},
        ]):
            chunks = forge_rag._chunk_repo(repo)
        ids = [c["id"] for c in chunks]
        assert "readme:myapp" in ids
        assert "deps:myapp" in ids
        assert "flask" in chunks[1]["text"]

    def test_chunk_no_readme(self, tmp_path):
        repo_path = tmp_path / "empty"
        repo_path.mkdir()
        repo = {"name": "empty", "path": str(repo_path)}
        with patch.object(forge_deps, "list_deps", return_value=[]):
            chunks = forge_rag._chunk_repo(repo)
        assert len(chunks) == 0


class TestChunkCVEs:
    def test_no_cves(self):
        with patch("forge.rag.forge_cve.list_cves", return_value=[]):
            chunks = forge_rag._chunk_cves()
        assert chunks == []

    def test_with_cves(self):
        with patch("forge.rag.forge_cve.list_cves", return_value=[
            {"id": "CVE-2024-1111", "ecosystem": "npm", "package": "lodash", "version": "4.17.21"},
        ]):
            chunks = forge_rag._chunk_cves()
        assert len(chunks) == 1
        assert "lodash" in chunks[0]["text"]
        assert chunks[0]["metadata"]["ecosystem"] == "npm"


class TestEnsureEmbeddingModel:
    def test_already_available(self):
        mock_run = MagicMock()
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "nomic-embed-text"
        with patch("subprocess.run", mock_run):
            assert forge_rag._ensure_embedding_model() is True

    def test_pull_needed(self):
        mock_list = MagicMock()
        mock_list.return_value.returncode = 0
        mock_list.return_value.stdout = ""
        mock_pull = MagicMock()
        mock_pull.return_value.returncode = 0
        mock_pull.return_value.stdout = ""
        with patch("subprocess.run", side_effect=[mock_list.return_value, mock_pull.return_value]):
            assert forge_rag._ensure_embedding_model() is True

    def test_ollama_not_installed(self):
        mock_run = MagicMock(side_effect=FileNotFoundError("ollama not found"))
        with patch("subprocess.run", mock_run):
            assert forge_rag._ensure_embedding_model() is False


class TestEmbed:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"embedding": [0.1, 0.2, 0.3]}).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        urlopen = MagicMock(return_value=mock_cm)
        with patch("urllib.request.urlopen", urlopen):
            result = forge_rag._ollama_embed("hello")
        assert result == [0.1, 0.2, 0.3]

    def test_network_error(self):
        urlopen = MagicMock(side_effect=OSError("connection failed"))
        with patch("urllib.request.urlopen", urlopen):
            result = forge_rag._ollama_embed("hello")
        assert result == []


class TestIndexCache:
    def test_load_empty(self, tmp_path):
        forge_rag.INDEX_FILE = os.path.join(tmp_path, "index.json")
        assert forge_rag._load_index() is None

    def test_save_and_load(self, tmp_path):
        forge_rag.INDEX_FILE = os.path.join(tmp_path, "index.json")
        data = {"model": "test", "chunks": [{"id": "c1", "text": "hello", "embedding": [0.1]}]}
        forge_rag._save_index(data)
        loaded = forge_rag._load_index()
        assert loaded["chunks"][0]["id"] == "c1"


class TestBuildIndex:
    def test_with_repos_and_cves(self, tmp_path, forge_config):
        forge_rag.INDEX_FILE = os.path.join(tmp_path, "index.json")
        repo_path = tmp_path / "myapp"
        repo_path.mkdir()
        (repo_path / "README.md").write_text("My app")
        forge_rag.cfg.add_repo(forge_config.load_config(),
            {"name": "myapp", "path": str(repo_path), "provider": "github", "url": "", "default_branch": "main"})
        forge_rag.cfg.save_config(forge_config.load_config())
        forge_deps.DEPS_FILE = os.path.join(tmp_path, "deps.json")
        forge_deps._save_deps_cache({"myapp": [{"name": "flask", "version": "2.0", "ecosystem": "pypi"}]})
        forge_rag.cve_forge_cve = forge_rag.forge_cve

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"embedding": _make_embedding()}).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_cm):
            with patch.object(forge_rag, "_ensure_embedding_model", return_value=True):
                count = forge_rag.build_index()
        assert count > 0

    def test_empty_workspace(self, tmp_path, forge_config):
        forge_rag.INDEX_FILE = os.path.join(tmp_path, "index.json")
        forge_deps.DEPS_FILE = os.path.join(tmp_path, "deps.json")
        forge_deps._save_deps_cache({})
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"embedding": _make_embedding()}).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        with patch("urllib.request.urlopen", return_value=mock_cm):
            with patch.object(forge_rag, "_ensure_embedding_model", return_value=True):
                count = forge_rag.build_index()
        assert count == 1


class TestSearch:
    def test_no_index(self):
        with patch.object(forge_rag, "_load_index", return_value=None):
            assert forge_rag.search("hello") == []

    def test_finds_relevant_chunk(self, tmp_path):
        forge_rag.INDEX_FILE = os.path.join(tmp_path, "index.json")
        forge_rag._save_index({
            "model": "test",
            "chunks": [
                {"id": "c1", "text": "about python", "embedding": [1.0, 0.0]},
                {"id": "c2", "text": "about java", "embedding": [0.0, 1.0]},
            ],
        })
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"embedding": [1.0, 0.0]}).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        with patch("urllib.request.urlopen", return_value=mock_cm):
            results = forge_rag.search("python", k=1)
        assert len(results) == 1
        assert results[0][1]["id"] == "c1"


class TestAsk:
    def test_ollama_not_installed(self):
        with patch("shutil.which", return_value=None):
            result = forge_rag.ask("hello")
        assert "Ollama is not installed" in result

    def test_builds_index_if_missing(self, tmp_path):
        forge_rag.INDEX_FILE = os.path.join(tmp_path, "index.json")
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"embedding": _make_embedding()}).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        gen_resp = MagicMock()
        gen_resp.read.return_value = json.dumps({"response": "I think the answer is..."}).encode()
        gen_cm = MagicMock()
        gen_cm.__enter__.return_value = gen_resp
        urlopen_returns = {
            "embeddings": mock_cm,
            "generate": gen_cm,
        }

        def urlopen_side(*args, **kwargs):
            url = args[0].full_url if hasattr(args[0], 'full_url') else ""
            if "embeddings" in url:
                return urlopen_returns["embeddings"]
            return urlopen_returns["generate"]

        with patch("shutil.which", return_value="/usr/bin/ollama"):
            with patch.object(forge_rag, "_ensure_embedding_model", return_value=True):
                with patch("urllib.request.urlopen", side_effect=urlopen_side):
                    with patch.object(forge_deps, "list_deps", return_value=[]):
                        result = forge_rag.ask("hello")
        assert "I think" in result