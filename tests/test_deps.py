import json
from forge import deps as forge_deps


class TestParseNpm:
    def test_parse_basic(self, tmp_path):
        data = {
            "packages": {
                "": {"name": "myapp"},
                "node_modules/lodash": {"version": "4.17.21"},
                "node_modules/express": {"version": "4.18.2"},
            }
        }
        f = tmp_path / "package-lock.json"
        f.write_text(json.dumps(data))
        result = forge_deps.parse_npm(str(f))
        assert len(result) == 2
        names = {d["name"] for d in result}
        assert names == {"lodash", "express"}
        assert all(d["ecosystem"] == "npm" for d in result)

    def test_parse_dependencies_section(self, tmp_path):
        data = {
            "dependencies": {
                "lodash": {"version": "4.17.21"},
            }
        }
        f = tmp_path / "package-lock.json"
        f.write_text(json.dumps(data))
        result = forge_deps.parse_npm(str(f))
        assert len(result) == 1
        assert result[0]["name"] == "lodash"

    def test_parse_empty(self, tmp_path):
        f = tmp_path / "package-lock.json"
        f.write_text("{}")
        result = forge_deps.parse_npm(str(f))
        assert result == []

    def test_parse_missing_file(self, tmp_path):
        result = forge_deps.parse_npm(str(tmp_path / "nonexistent.json"))
        assert result == []


class TestParseCargo:
    def test_parse_basic(self, tmp_path):
        content = """[[package]]
name = "serde"
version = "1.0.188"

[[package]]
name = "toml"
version = "0.7.8"
"""
        f = tmp_path / "Cargo.lock"
        f.write_text(content)
        result = forge_deps.parse_cargo(str(f))
        assert len(result) == 2
        names = {d["name"] for d in result}
        assert names == {"serde", "toml"}
        assert all(d["ecosystem"] == "cargo" for d in result)

    def test_parse_empty(self, tmp_path):
        f = tmp_path / "Cargo.lock"
        f.write_text("")
        result = forge_deps.parse_cargo(str(f))
        assert isinstance(result, list)
        assert result == []


class TestParsePyproject:
    def test_parse_basic(self, tmp_path):
        content = """[project]
name = "my-pkg"
version = "0.1.0"
dependencies = [
    "requests>=2.28.0",
    "click>=8.0",
]
"""
        f = tmp_path / "pyproject.toml"
        f.write_text(content)
        result = forge_deps.parse_pyproject(str(f))
        assert len(result) == 2
        names = {d["name"] for d in result}
        assert names == {"requests", "click"}
        assert all(d["ecosystem"] == "pypi" for d in result)

    def test_parse_with_optional(self, tmp_path):
        content = """[project]
name = "my-pkg"
version = "0.1.0"
dependencies = ["rich"]

[project.optional-dependencies]
dev = ["pytest", "ruff"]
"""
        f = tmp_path / "pyproject.toml"
        f.write_text(content)
        result = forge_deps.parse_pyproject(str(f))
        assert len(result) == 3
        optional = [d for d in result if d.get("optional")]
        assert len(optional) == 2


class TestParseRequirements:
    def test_parse_basic(self, tmp_path):
        content = "flask>=2.0\nrequests==2.28.0\nnumpy\n"
        f = tmp_path / "requirements.txt"
        f.write_text(content)
        result = forge_deps.parse_requirements(str(f))
        assert len(result) == 3
        assert result[0]["name"] == "flask"
        assert result[0]["ecosystem"] == "pypi"

    def test_skips_comments_and_blanks(self, tmp_path):
        content = "# comment\nflask>=2.0\n\nnumpy\n-r other.txt\n"
        f = tmp_path / "requirements.txt"
        f.write_text(content)
        result = forge_deps.parse_requirements(str(f))
        assert len(result) == 2


class TestParseGosum:
    def test_parse_basic(self, tmp_path):
        content = "golang.org/x/net v0.21.0 h1:abcdef\n"
        f = tmp_path / "go.sum"
        f.write_text(content)
        result = forge_deps.parse_gosum(str(f))
        assert len(result) == 1
        assert result[0]["name"] == "golang.org/x/net"
        assert result[0]["version"] == "v0.21.0"
        assert result[0]["ecosystem"] == "go"


class TestParseGemfile:
    def test_parse_basic(self, tmp_path):
        content = """GEM
  remote: https://rubygems.org/
  specs:
    rake (13.0.6)
    rspec (3.12.0)

PLATFORMS
  ruby

DEPENDENCIES
  rake
  rspec
"""
        f = tmp_path / "Gemfile.lock"
        f.write_text(content)
        result = forge_deps.parse_gemfile(str(f))
        assert len(result) == 2
        names = {d["name"] for d in result}
        assert names == {"rake", "rspec"}
        assert all(d["ecosystem"] == "rubygems" for d in result)


class TestFindLockfiles:
    def test_finds_existing_lockfiles(self, tmp_path):
        (tmp_path / "package-lock.json").write_text("{}")
        (tmp_path / "Cargo.lock").write_text("")
        files = forge_deps._find_lockfiles(str(tmp_path))
        assert "package-lock.json" in files
        assert "Cargo.lock" in files

    def test_returns_empty_for_empty_dir(self, tmp_path):
        files = forge_deps._find_lockfiles(str(tmp_path))
        assert files == {}


class TestParseRepoDeps:
    def test_parses_all_lockfiles(self, tmp_path):
        (tmp_path / "package-lock.json").write_text(
            json.dumps({"packages": {"node_modules/lodash": {"version": "4.17.21"}}})
        )
        (tmp_path / "requirements.txt").write_text("flask>=2.0\n")
        result = forge_deps.parse_repo_deps(str(tmp_path))
        assert len(result) == 2
        ecosystems = {d["ecosystem"] for d in result}
        assert ecosystems == {"npm", "pypi"}


class TestCache:
    def test_save_and_load(self, tmp_path, monkeypatch):
        monkeypatch.setattr(forge_deps, "DEPS_FILE", str(tmp_path / "deps.json"))
        forge_deps.update_deps_for_repo("test-repo", "nonexistent")
        cache = forge_deps.get_deps()
        assert "test-repo" in cache
        assert cache["test-repo"] == []

    def test_get_deps_filter(self, tmp_path, monkeypatch):
        monkeypatch.setattr(forge_deps, "DEPS_FILE", str(tmp_path / "deps.json"))
        cache = {"repo-a": [{"name": "lodash", "version": "1.0", "ecosystem": "npm"}]}
        forge_deps._save_deps_cache(cache)
        result = forge_deps.get_deps("repo-a")
        assert len(result) == 1
        assert result[0]["name"] == "lodash"


class TestListDeps:
    def test_list_all(self, tmp_path, monkeypatch):
        monkeypatch.setattr(forge_deps, "DEPS_FILE", str(tmp_path / "deps.json"))
        cache = {
            "repo-a": [{"name": "lodash", "version": "1.0", "ecosystem": "npm"}],
            "repo-b": [{"name": "serde", "version": "2.0", "ecosystem": "cargo"}],
        }
        forge_deps._save_deps_cache(cache)
        all_deps = forge_deps.list_deps()
        assert len(all_deps) == 2

    def test_filter_by_ecosystem(self, tmp_path, monkeypatch):
        monkeypatch.setattr(forge_deps, "DEPS_FILE", str(tmp_path / "deps.json"))
        cache = {
            "repo-a": [
                {"name": "lodash", "version": "1.0", "ecosystem": "npm"},
                {"name": "flask", "version": "2.0", "ecosystem": "pypi"},
            ]
        }
        forge_deps._save_deps_cache(cache)
        filtered = forge_deps.list_deps(ecosystem="npm")
        assert len(filtered) == 1
        assert filtered[0]["name"] == "lodash"

    def test_filter_by_repo(self, tmp_path, monkeypatch):
        monkeypatch.setattr(forge_deps, "DEPS_FILE", str(tmp_path / "deps.json"))
        cache = {
            "repo-a": [{"name": "lodash", "version": "1.0", "ecosystem": "npm"}],
            "repo-b": [{"name": "serde", "version": "2.0", "ecosystem": "cargo"}],
        }
        forge_deps._save_deps_cache(cache)
        deps_a = forge_deps.list_deps(repo_name="repo-a")
        assert len(deps_a) == 1
        assert deps_a[0]["name"] == "lodash"

    def test_deps_count(self, tmp_path, monkeypatch):
        monkeypatch.setattr(forge_deps, "DEPS_FILE", str(tmp_path / "deps.json"))
        cache = {
            "repo-a": [{"name": "a", "version": "1", "ecosystem": "npm"}],
            "repo-b": [{"name": "b", "version": "2", "ecosystem": "cargo"}],
        }
        forge_deps._save_deps_cache(cache)
        assert forge_deps.deps_count() == 2
        assert forge_deps.deps_count("repo-a") == 1
