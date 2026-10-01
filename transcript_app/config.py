"""Application configuration: .env plus CLI overrides.

The LLM endpoint is any OpenAI-compatible chat completions API. Nothing here
is tied to a specific gateway implementation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _env_locations() -> list[Path]:
    """Where to look for .env, in order of precedence.

    Works both from a checkout (project root) and from an installed package
    (current working directory, then an optional ~/.config/tubestoevsky/.env).
    """
    locations = [Path.cwd() / ".env", PACKAGE_ROOT / ".env"]
    locations.append(Path.home() / ".config" / "tubestoevsky" / ".env")
    return locations


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
    """Read .env (project root) and apply CLI overrides."""
    for env_file in _env_locations():
        if env_file.is_file():
            load_dotenv(env_file, override=False)

    base_url = _normalize_base_url(os.getenv("LLM_BASE_URL", "http://127.0.0.1:4000"))
    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key:
        raise SystemExit("LLM_API_KEY is not set: fill in .env (see .env.example)")

    return Config(
        base_url=base_url,
        api_key=api_key,
        model=model or os.getenv("LLM_MODEL", "gpt-6-luna"),
        lang=(lang or os.getenv("TRANSCRIPT_LANG", "en")).lower(),
        output_dir=Path(output_dir or os.getenv("OUTPUT_DIR", ".")).expanduser().resolve(),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
        timeout=int(os.getenv("LLM_TIMEOUT", "1800")),
        cookies=os.getenv("YTDLP_COOKIES") or None,
        cookies_from_browser=os.getenv("YTDLP_COOKIES_FROM_BROWSER") or None,
    )
