import pytest

pytestmark = pytest.mark.unit

from src.utils.secrets import load_secret_values


class TestLoadSecretValues:
    def test_prefers_environment_variables(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "env-key-1")
        monkeypatch.setenv("GEMINI_API_KEY_2", "env-key-2")
        monkeypatch.delenv("GEMINI_API_KEY_FILE", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY_PATH", raising=False)

        values = load_secret_values("GEMINI_API_KEY")

        assert values == ["env-key-1", "env-key-2"]

    def test_supports_file_indirection(self, monkeypatch, tmp_path):
        secret_file = tmp_path / "gemini_api_key"
        secret_file.write_text("file-key-1\nfile-key-2\n")

        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY_FILE", str(secret_file))

        values = load_secret_values("GEMINI_API_KEY")

        assert values == ["file-key-1", "file-key-2"]

    def test_falls_back_to_secret_directories(self, monkeypatch, tmp_path):
        secret_dir = tmp_path / "nested" / "secrets"
        secret_dir.mkdir(parents=True)
        (secret_dir / "GEMINI_API_KEY").write_text("dir-key")

        for name in [
            "GEMINI_API_KEY",
            "GEMINI_API_KEY_2",
            "GEMINI_API_KEY_FILE",
            "GEMINI_API_KEY_PATH",
            "GEMINI_API_KEY_DIR",
            "GEMINI_API_KEY_DIRECTORY",
        ]:
            monkeypatch.delenv(name, raising=False)

        values = load_secret_values("GEMINI_API_KEY", extra_dirs=[secret_dir])

        assert values == ["dir-key"]
