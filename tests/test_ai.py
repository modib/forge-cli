import json
import platform
from ws import ai


class TestDetectHardware:
    def test_hardware_profile_structure(self):
        profile = ai.detect_hardware()
        assert "platform" in profile
        assert "arch" in profile
        assert "cpu" in profile
        assert "memory" in profile
        assert "gpu" in profile
        assert "disk" in profile

    def test_platform_detected(self):
        profile = ai.detect_hardware()
        assert profile["platform"] == platform.system()
        assert profile["arch"] == platform.machine()

    def test_cpu_has_cores(self):
        profile = ai.detect_hardware()
        assert profile["cpu"]["cores"] > 0

    def test_gpu_list(self):
        profile = ai.detect_hardware()
        assert len(profile["gpu"]) >= 1
        assert profile["gpu"][0]["vendor"] in ("nvidia", "amd", "none")

    def test_memory_detected(self):
        profile = ai.detect_hardware()
        mem = profile["memory"]
        assert "total_gb" in mem
        assert mem["total_gb"] > 0

    def test_disk_detected(self):
        profile = ai.detect_hardware()
        disk = profile["disk"]
        assert "total_gb" in disk
        assert disk["total_gb"] > 0

    def test_json_output_parses(self, capsys):
        class FakeArgs:
            json = True
            backend = ""
        ai.detect_and_print(FakeArgs())
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "cpu" in data
        assert "memory" in data


class TestSuggestModel:
    def test_suggests_large_model_for_16gb(self):
        profile = {"memory": {"total_gb": 16}, "gpu": [{"vendor": "none", "model": "none"}]}
        model = ai.suggest_model(profile)
        assert model == "qwen2.5-coder:7b"

    def test_suggests_medium_model_for_8gb(self):
        profile = {"memory": {"total_gb": 8}, "gpu": [{"vendor": "none", "model": "none"}]}
        model = ai.suggest_model(profile)
        assert model == "phi-4-mini:3.8b"

    def test_suggests_small_model_for_low_ram(self):
        profile = {"memory": {"total_gb": 4}, "gpu": [{"vendor": "none", "model": "none"}]}
        model = ai.suggest_model(profile)
        assert model == "qwen2.5-coder:1.5b"

    def test_suggests_apple_silicon_mlx_large(self):
        profile = {"memory": {"total_gb": 16}, "apple_silicon": True}
        model = ai.suggest_model(profile, backend="mlx")
        assert "7B" in model or "7b" in model

    def test_suggests_apple_silicon_mlx_8gb(self):
        profile = {"memory": {"total_gb": 8}, "apple_silicon": True}
        model = ai.suggest_model(profile, backend="mlx")
        assert "7B" in model or "7b" in model

    def test_suggests_apple_silicon_mlx_low_ram(self):
        profile = {"memory": {"total_gb": 4}, "apple_silicon": True}
        model = ai.suggest_model(profile, backend="mlx")
        assert model == "Qwen2.5-Coder-1.5B-Instruct"

    def test_suggests_apple_silicon_auto_backend(self):
        profile = {"memory": {"total_gb": 8}, "apple_silicon": True}
        backend = ai._recommend_backend(profile)
        assert backend == "mlx"

    def test_suggests_intel_auto_backend(self):
        profile = {"memory": {"total_gb": 8}, "apple_silicon": False}
        backend = ai._recommend_backend(profile)
        assert backend == "ollama"


class TestCheckOllama:
    def test_check_ollama_returns_bool(self):
        result = ai.check_ollama()
        assert isinstance(result, bool)


class TestResolveIntent:
    def test_status_intent(self):
        assert ai.resolve_intent("show me dirty repos") == "status"
        assert ai.resolve_intent("what's the status") == "status"
        assert ai.resolve_intent("status") == "status"

    def test_scan_intent(self):
        assert ai.resolve_intent("scan for new repos") == "scan"
        assert ai.resolve_intent("discover repos") == "scan"

    def test_health_intent(self):
        assert ai.resolve_intent("health check") == "health"
        assert ai.resolve_intent("check dev environment") == "health"

    def test_doctor_intent(self):
        assert ai.resolve_intent("doctor") == "doctor"
        assert ai.resolve_intent("what's wrong") == "doctor"

    def test_feature_list_intent(self):
        assert ai.resolve_intent("list features") == "feature_list"
        assert ai.resolve_intent("show features") == "feature_list"

    def test_log_intent(self):
        assert ai.resolve_intent("show log") == "log"
        assert ai.resolve_intent("recent sessions") == "log"

    def test_help_intent(self):
        assert ai.resolve_intent("help") == "help"
        assert ai.resolve_intent("what can you do") == "help"

    def test_unknown_intent(self):
        assert ai.resolve_intent("do something crazy") is None


class TestExecNl:
    def test_unknown_query(self):
        result = ai.exec_nl("do something impossible")
        assert "error" in result

    def test_dry_run(self):
        result = ai.exec_nl("status", dry_run=True)
        assert result["intent"] == "status"
        assert result["command"] == "ws status"

    def test_dry_run_scans(self):
        result = ai.exec_nl("scan", dry_run=True)
        assert result["intent"] == "scan"
        assert result["command"] == "ws scan"


class TestAiConfig:
    def test_config_set_and_get(self, ws_config):
        class FakeArgs:
            key = "provider"
            value = "ollama"
        ai.ai_config_cmd(FakeArgs())
        c = ws_config.load_config()
        assert c["ai"]["provider"] == "ollama"

    def test_config_set_nested(self, ws_config):
        class FakeArgs:
            key = "routing.local"
            value = "phi-4-mini:3.8b"
        ai.ai_config_cmd(FakeArgs())
        c = ws_config.load_config()
        assert c["ai"]["routing"]["local"] == "phi-4-mini:3.8b"

    def test_config_unset(self, ws_config):
        c = ws_config.load_config()
        c["ai"] = {"provider": "ollama"}
        ws_config.save_config(c)
        class FakeArgs:
            key = "provider"
            value = None
        ai.ai_config_cmd(FakeArgs())
        c = ws_config.load_config()
        assert "provider" not in c["ai"]

    def test_config_show(self, ws_config):
        c = ws_config.load_config()
        c["ai"] = {"provider": "ollama"}
        ws_config.save_config(c)
        class FakeArgs:
            key = None
            value = None
        ai.ai_config_cmd(FakeArgs())
        c = ws_config.load_config()
        assert c["ai"]["provider"] == "ollama"

    def test_config_coerce_bool(self, ws_config):
        class FakeArgs:
            key = "enabled"
            value = "true"
        ai.ai_config_cmd(FakeArgs())
        c = ws_config.load_config()
        assert c["ai"]["enabled"] is True

    def test_config_coerce_int(self, ws_config):
        class FakeArgs:
            key = "timeout"
            value = "30"
        ai.ai_config_cmd(FakeArgs())
        c = ws_config.load_config()
        assert c["ai"]["timeout"] == 30