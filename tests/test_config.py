import argparse
from pathlib import Path

import pytest

from transcript_app.__main__ import main
from transcript_app.config import (
    load_config,
    read_saved_config,
    write_saved_config,
)


def test_saved_config_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"

    write_saved_config({"LLM_MODEL": "test-model", "OUTPUT_DIR": str(tmp_path)}, path)
    saved = read_saved_config(path)

    assert saved == {"LLM_MODEL": "test-model", "OUTPUT_DIR": str(tmp_path)}


def test_environment_overrides_saved_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "env-key")
    monkeypatch.setenv("LLM_MODEL", "env-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.9")
    monkeypatch.setenv("LLM_TIMEOUT", "123")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "env"))
    monkeypatch.setenv("YTDLP_COOKIES", "/tmp/env-cookies")
    monkeypatch.setenv("YTDLP_COOKIES_FROM_BROWSER", "chrome")
    monkeypatch.delenv("TRANSCRIPT_LANG", raising=False)
    monkeypatch.setattr("transcript_app.config._env_locations", list)
    write_saved_config(
        {
            "LLM_API_KEY": "config-key",
            "LLM_MODEL": "config-model",
            "TRANSCRIPT_LANG": "de",
            "LLM_BASE_URL": "https://config.example/v1",
            "LLM_TEMPERATURE": "0.1",
            "LLM_TIMEOUT": "456",
            "OUTPUT_DIR": str(tmp_path / "config"),
            "YTDLP_COOKIES": "/tmp/config-cookies",
            "YTDLP_COOKIES_FROM_BROWSER": "safari",
        },
        tmp_path / "config.yaml",
    )
    monkeypatch.setattr("transcript_app.config.CONFIG_PATH", tmp_path / "config.yaml")

    cfg = load_config()

    assert cfg.api_key == "env-key"
    assert cfg.model == "env-model"
    assert cfg.lang == "de"
    assert cfg.base_url == "https://env.example/v1"
    assert cfg.temperature == 0.9
    assert cfg.timeout == 123
    assert cfg.output_dir == tmp_path / "env"
    assert cfg.cookies == "/tmp/env-cookies"
    assert cfg.cookies_from_browser == "chrome"


def test_config_cli_set_and_get(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "config.yaml"
    monkeypatch.setattr("transcript_app.config.CONFIG_PATH", config_path)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    assert main(["config", "set", "LLM_MODEL", "test-model"]) == 0
    assert main(["config", "get", "LLM_MODEL"]) == 0
    assert (
        capsys.readouterr().out
        == "Saved LLM_MODEL to " + str(config_path) + "\ntest-model\n"
    )


def test_config_get_environment_overrides_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_saved_config({"LLM_MODEL": "config-model"}, tmp_path / "config.yaml")
    monkeypatch.setattr("transcript_app.config.CONFIG_PATH", tmp_path / "config.yaml")
    monkeypatch.setenv("LLM_MODEL", "env-model")

    assert main(["config", "get", "LLM_MODEL", "--show-source"]) == 0

    assert capsys.readouterr().out == "env-model\tenvironment\n"


def test_config_overrides_env_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("LLM_MODEL=env-file-model\nLLM_TIMEOUT=90\n", encoding="utf-8")
    write_saved_config({"LLM_MODEL": "config-model"}, tmp_path / "config.yaml")
    monkeypatch.setattr("transcript_app.config._env_locations", lambda: [env_path])
    monkeypatch.setattr("transcript_app.config.CONFIG_PATH", tmp_path / "config.yaml")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_TIMEOUT", raising=False)

    assert main(["config", "get", "LLM_MODEL", "--show-source"]) == 0
    assert main(["config", "get", "LLM_TIMEOUT", "--show-source"]) == 0

    assert capsys.readouterr().out == "config-model\tconfig\n90\t.env\n"


def test_legacy_invocation_is_equivalent_to_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call = {}

    def fake_run(args: object) -> int:
        call["args"] = args
        return 0

    monkeypatch.setattr("transcript_app.__main__._run", fake_run)

    assert main(["https://example.com", "--lang", "en"]) == 0

    args = call["args"]
    assert args.url == "https://example.com"
    assert args.lang == "en"


def test_global_help_and_version(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []

    def fake_parse_args(tokens: list[str]) -> argparse.Namespace:
        captured.append(tokens)
        return argparse.Namespace(command="run")

    monkeypatch.setattr("transcript_app.__main__.parse_args", fake_parse_args)
    monkeypatch.setattr("transcript_app.__main__._run", lambda _args: 0)

    assert main(["--version"]) == 0
    assert main(["--help"]) == 0

    assert captured == [["--version"], ["--help"]]
