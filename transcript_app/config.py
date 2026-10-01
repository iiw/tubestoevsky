"""Application configuration: YAML, .env, environment, and CLI overrides.

The LLM endpoint is any OpenAI-compatible chat completions API. Nothing here
is tied to a specific gateway implementation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import dotenv_values

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = Path.home() / ".tubestoevsky"
CONFIG_PATH = CONFIG_DIR / "config.yaml"

CONFIG_KEYS = (
    "LLM_BASE_URL",
    "LLM_API_KEY",
    "LLM_MODEL",
    "TRANSCRIPT_LANG",
    "OUTPUT_DIR",
    "LLM_TEMPERATURE",
    "LLM_TIMEOUT",
    "YTDLP_COOKIES",
    "YTDLP_COOKIES_FROM_BROWSER",
)

CONFIG_DEFAULTS = {
    "LLM_BASE_URL": "http://127.0.0.1:4000",
    "LLM_API_KEY": "",
    "LLM_MODEL": "gpt-6-luna",
    "TRANSCRIPT_LANG": "en",
    "OUTPUT_DIR": ".",
    "LLM_TEMPERATURE": "0.3",
    "LLM_TIMEOUT": "1800",
    "YTDLP_COOKIES": "",
    "YTDLP_COOKIES_FROM_BROWSER": "",
}


def _env_locations() -> list[Path]:
    """Where to look for .env, in order of precedence.

    Works both from a checkout (project root) and from an installed package
    (current working directory, then an optional ~/.config/tubestoevsky/.env).
    """
    locations = [Path.cwd() / ".env", PACKAGE_ROOT / ".env"]
    locations.append(Path.home() / ".config" / "tubestoevsky" / ".env")
    return locations


def _read_env_files() -> dict[str, str]:
    """Read .env values without promoting them to process environment."""
    values: dict[str, str | None] = {}
    for env_file in _env_locations():
        if env_file.is_file():
            values.update(dotenv_values(env_file))
    return {key: value for key, value in values.items() if isinstance(value, str)}


def _normalize_base_url(raw: str) -> str:
    """Point the URL at the API root: add /v1 when no path is given.

    Accepts both "http://host:4000" and "http://host:4000/v1".
    """
    url = raw.strip().rstrip("/")
    if not url:
        return url
    path = url.split("://", 1)[-1].split("/", 1)
    has_path = len(path) > 1 and path[1]
    return url if has_path else f"{url}/v1"


def _coerce_config_value(key: str, value: object) -> str:
    """Represent YAML scalars consistently when writing and displaying them."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _is_config_key(key: object) -> bool:
    return isinstance(key, str) and key in CONFIG_KEYS


def read_saved_config(config_path: Path | None = None) -> dict[str, str]:
    """Read user configuration without letting it override environment."""
    path = config_path or CONFIG_PATH
    if not path.is_file():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise SystemExit(f"Cannot read configuration {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise SystemExit(f"Configuration must be a mapping: {path}")
    return {
        key: _coerce_config_value(key, value)
        for key, value in loaded.items()
        if _is_config_key(key)
    }


def write_saved_config(values: dict[str, str], config_path: Path | None = None) -> Path:
    """Persist user configuration to ~/.tubestoevsky/config.yaml."""
    path = config_path or CONFIG_PATH
    unknown = set(values) - set(CONFIG_KEYS)
    if unknown:
        raise SystemExit(f"Unknown config keys: {', '.join(sorted(unknown))}")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(
                values,
                default_flow_style=False,
                sort_keys=True,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        raise SystemExit(f"Cannot write configuration {path}: {exc}") from exc
    return path


def _resolve_setting(
    key: str,
    saved: dict[str, str],
    env_file_values: dict[str, str],
) -> tuple[str, str]:
    if key in os.environ:
        return os.environ[key], "environment"
    if key in saved:
        return saved[key], "config"
    if key in env_file_values:
        return env_file_values[key], ".env"
    return CONFIG_DEFAULTS[key], "default"


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str
    model: str
    lang: str
    output_dir: Path
    temperature: float
    timeout: int
    cookies: str | None
    cookies_from_browser: str | None


def load_config(
    lang: str | None = None,
    output_dir: str | None = None,
    model: str | None = None,
) -> Config:
    """Resolve settings: CLI flags, environment, YAML, .env, then defaults."""
    saved = read_saved_config()
    env_file_values = _read_env_files()
    resolved = {
        key: _resolve_setting(key, saved, env_file_values)[0] for key in CONFIG_KEYS
    }

    base_url = _normalize_base_url(resolved["LLM_BASE_URL"])
    api_key = resolved["LLM_API_KEY"]
    if not api_key:
        raise SystemExit("LLM_API_KEY is not set: use config, .env, or environment")

    return Config(
        base_url=base_url,
        api_key=api_key,
        model=model or resolved["LLM_MODEL"],
        lang=(lang or resolved["TRANSCRIPT_LANG"]).lower(),
        output_dir=Path(output_dir or resolved["OUTPUT_DIR"]).expanduser().resolve(),
        temperature=float(resolved["LLM_TEMPERATURE"]),
        timeout=int(resolved["LLM_TIMEOUT"]),
        cookies=resolved["YTDLP_COOKIES"] or None,
        cookies_from_browser=resolved["YTDLP_COOKIES_FROM_BROWSER"] or None,
    )
