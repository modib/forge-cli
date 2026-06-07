import json
import os
from unittest.mock import patch, MagicMock
from forge import cve as forge_cve
from forge import deps as forge_deps


class TestEcosystemMap:
    def test_npm(self):
        assert forge_cve._osv_ecosystem({"ecosystem": "npm"}) == "npm"

    def test_cargo(self):
        assert forge_cve._osv_ecosystem({"ecosystem": "cargo"}) == "crates.io"

    def test_pypi(self):
        assert forge_cve._osv_ecosystem({"ecosystem": "pypi"}) == "PyPI"

    def test_go(self):
        assert forge_cve._osv_ecosystem({"ecosystem": "go"}) == "Go"

    def test_rubygems(self):
        assert forge_cve._osv_ecosystem({"ecosystem": "rubygems"}) == "RubyGems"

    def test_unknown(self):
        assert forge_cve._osv_ecosystem({"ecosystem": "unknown"}) == ""


class TestDepKey:
    def test_valid(self):
        key = forge_cve._dep_key({"name": "lodash", "version": "4.17.21", "ecosystem": "npm"})
        assert key == "npm:lodash@4.17.21"

    def test_missing_name(self):
        assert forge_cve._dep_key({"version": "1.0", "ecosystem": "npm"}) is None

    def test_missing_version(self):
        assert forge_cve._dep_key({"name": "foo", "ecosystem": "npm"}) is None

    def test_unknown_ecosystem(self):
        assert forge_cve._dep_key({"name": "foo", "version": "1.0", "ecosystem": "unknown"}) is None


class TestCache:
    def test_load_empty(self, tmp_path):
        forge_cve.CVE_FILE = os.path.join(tmp_path, "cve.json")
        assert forge_cve._load_cache() == {}

    def test_load_corrupt(self, tmp_path):
        f = tmp_path / "cve.json"
        f.write_text("not json")
        forge_cve.CVE_FILE = str(f)
        assert forge_cve._load_cache() == {}

    def test_save_and_load(self, tmp_path):
        forge_cve.CVE_FILE = os.path.join(tmp_path, "cve.json")
        forge_cve._save_cache({"npm:lodash@4.17.21": [{"id": "CVE-2024-1234"}]})
        loaded = forge_cve._load_cache()
        assert len(loaded["npm:lodash@4.17.21"]) == 1
        assert loaded["npm:lodash@4.17.21"][0]["id"] == "CVE-2024-1234"

    def test_save_creates_dir(self, tmp_path):
        d = tmp_path / "subdir" / "nested"
        forge_cve.CVE_FILE = os.path.join(str(d), "cve.json")
        forge_cve._save_cache({"a": [{"id": "CVE-1"}]})
        assert os.path.exists(forge_cve.CVE_FILE)


class TestQuery:
    def test_query_osv_success(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "vulns": [
                {"id": "CVE-2024-1234", "modified": "2024-01-01T00:00:00Z"}
            ]
        }).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        urlopen = MagicMock(return_value=mock_cm)
        with patch("urllib.request.urlopen", urlopen):
            result = forge_cve._query_osv("lodash", "npm", "4.17.21")
        assert len(result) == 1
        assert result[0]["id"] == "CVE-2024-1234"
        assert result[0]["summary"] == ""

    def test_query_osv_empty(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"vulns": []}).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        urlopen = MagicMock(return_value=mock_cm)
        with patch("urllib.request.urlopen", urlopen):
            result = forge_cve._query_osv("safe-package", "npm", "1.0.0")
        assert result == []

    def test_query_osv_network_error(self):
        urlopen = MagicMock(side_effect=OSError("Connection failed"))
        with patch("urllib.request.urlopen", urlopen):
            result = forge_cve._query_osv("lodash", "npm", "4.17.21")
        assert result == []

    def test_query_osv_decode_error(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not json"
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        urlopen = MagicMock(return_value=mock_cm)
        with patch("urllib.request.urlopen", urlopen):
            result = forge_cve._query_osv("lodash", "npm", "4.17.21")
        assert result == []


class TestFetchDetail:
    def test_fetch_success(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "id": "CVE-2024-1234",
            "summary": "Test vulnerability",
            "aliases": ["GHSA-xxxx"],
            "references": [],
            "database_specific": {"severity": "HIGH"},
        }).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        urlopen = MagicMock(return_value=mock_cm)
        with patch("urllib.request.urlopen", urlopen):
            result = forge_cve._fetch_vuln_detail("CVE-2024-1234")
        assert result["id"] == "CVE-2024-1234"
        assert result["summary"] == "Test vulnerability"
        assert "GHSA-xxxx" in result["aliases"]
        assert result["cvss_score"] == 7.5

    def test_fetch_network_error(self):
        urlopen = MagicMock(side_effect=OSError("timeout"))
        with patch("urllib.request.urlopen", urlopen):
            result = forge_cve._fetch_vuln_detail("CVE-2024-9999")
        assert result is None


class TestRefresh:
    def test_refresh_empty_deps(self, tmp_path):
        forge_cve.CVE_FILE = os.path.join(tmp_path, "cve.json")
        forge_deps.DEPS_FILE = os.path.join(tmp_path, "deps.json")
        forge_deps._save_deps_cache({})
        result = forge_cve.refresh()
        assert result["queried"] == 0
        assert result["vulns_found"] == 0

    def test_refresh_with_deps(self, tmp_path):
        forge_cve.CVE_FILE = os.path.join(tmp_path, "cve.json")
        forge_deps.DEPS_FILE = os.path.join(tmp_path, "deps.json")
        forge_deps._save_deps_cache({
            "myapp": [
                {"name": "lodash", "version": "4.17.21", "ecosystem": "npm"},
            ]
        })
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "vulns": [{"id": "CVE-2024-1234", "modified": "2024-01-01T00:00:00Z"}]
        }).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        urlopen = MagicMock(return_value=mock_cm)
        with patch("urllib.request.urlopen", urlopen):
            result = forge_cve.refresh()
        assert result["queried"] == 1
        assert result["vulns_found"] == 1
        assert result["total_cached"] == 1

    def test_refresh_skips_cached(self, tmp_path):
        forge_cve.CVE_FILE = os.path.join(tmp_path, "cve.json")
        forge_cve._save_cache({"npm:lodash@4.17.21": [{"id": "CVE-2024-1234"}]})
        forge_deps.DEPS_FILE = os.path.join(tmp_path, "deps.json")
        forge_deps._save_deps_cache({
            "myapp": [
                {"name": "lodash", "version": "4.17.21", "ecosystem": "npm"},
            ]
        })
        urlopen = MagicMock()
        with patch("urllib.request.urlopen", urlopen):
            result = forge_cve.refresh()
        assert result["queried"] == 0
        assert result["vulns_found"] == 0
        assert result["total_cached"] == 1
        urlopen.assert_not_called()


class TestList:
    def test_list_empty(self, tmp_path):
        forge_cve.CVE_FILE = os.path.join(tmp_path, "cve.json")
        forge_cve._save_cache({})
        forge_deps.DEPS_FILE = os.path.join(tmp_path, "deps.json")
        forge_deps._save_deps_cache({})
        cves = forge_cve.list_cves()
        assert cves == []

    def test_list_with_cves(self, tmp_path):
        forge_cve.CVE_FILE = os.path.join(tmp_path, "cve.json")
        forge_cve._save_cache({
            "npm:lodash@4.17.21": [{"id": "CVE-2024-1111"}],
        })
        forge_deps.DEPS_FILE = os.path.join(tmp_path, "deps.json")
        forge_deps._save_deps_cache({
            "myapp": [
                {"name": "lodash", "version": "4.17.21", "ecosystem": "npm"},
            ]
        })
        cves = forge_cve.list_cves()
        assert len(cves) == 1
        assert cves[0]["id"] == "CVE-2024-1111"

    def test_list_filter_ecosystem(self, tmp_path):
        forge_cve.CVE_FILE = os.path.join(tmp_path, "cve.json")
        forge_cve._save_cache({
            "npm:lodash@4.17.21": [{"id": "CVE-2024-1111"}],
        })
        forge_deps.DEPS_FILE = os.path.join(tmp_path, "deps.json")
        forge_deps._save_deps_cache({
            "myapp": [
                {"name": "lodash", "version": "4.17.21", "ecosystem": "npm"},
                {"name": "serde", "version": "1.0.0", "ecosystem": "cargo"},
            ]
        })
        cves = forge_cve.list_cves(ecosystem="cargo")
        assert cves == []


class TestReport:
    def test_report_empty(self, tmp_path):
        forge_cve.CVE_FILE = os.path.join(tmp_path, "cve.json")
        forge_cve._save_cache({})
        forge_deps.DEPS_FILE = os.path.join(tmp_path, "deps.json")
        forge_deps._save_deps_cache({})
        r = forge_cve.report()
        assert r["total"] == 0

    def test_report_with_data(self, tmp_path):
        forge_cve.CVE_FILE = os.path.join(tmp_path, "cve.json")
        forge_cve._save_cache({
            "npm:lodash@4.17.21": [{"id": "CVE-2024-1111"}],
        })
        forge_deps.DEPS_FILE = os.path.join(tmp_path, "deps.json")
        forge_deps._save_deps_cache({
            "myapp": [
                {"name": "lodash", "version": "4.17.21", "ecosystem": "npm"},
            ]
        })
        r = forge_cve.report()
        assert r["total"] == 1
        assert r["by_severity"]["unknown"] == 1


class TestDescribe:
    def test_describe_fetch_and_cache(self, tmp_path):
        forge_cve.CVE_FILE = os.path.join(tmp_path, "cve.json")
        forge_cve._save_cache({})
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "id": "CVE-2024-1234",
            "summary": "Test vuln",
            "aliases": [],
            "references": [],
        }).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        urlopen = MagicMock(return_value=mock_cm)
        with patch("urllib.request.urlopen", urlopen):
            result = forge_cve.describe("CVE-2024-1234")
        assert result["id"] == "CVE-2024-1234"
        assert result["summary"] == "Test vuln"
        cache = forge_cve._load_cache()
        assert "_detail:CVE-2024-1234" in cache

    def test_describe_uses_cache(self, tmp_path):
        forge_cve.CVE_FILE = os.path.join(tmp_path, "cve.json")
        forge_cve._save_cache({
            "_detail:CVE-2024-1234": {"id": "CVE-2024-1234", "summary": "cached", "aliases": [], "cvss_score": None},
        })
        urlopen = MagicMock()
        with patch("urllib.request.urlopen", urlopen):
            result = forge_cve.describe("CVE-2024-1234")
        assert result["summary"] == "cached"
        urlopen.assert_not_called()

    def test_describe_network_error(self, tmp_path):
        forge_cve.CVE_FILE = os.path.join(tmp_path, "cve.json")
        forge_cve._save_cache({})
        urlopen = MagicMock(side_effect=OSError("timeout"))
        with patch("urllib.request.urlopen", urlopen):
            result = forge_cve.describe("CVE-2024-9999")
        assert result is None
