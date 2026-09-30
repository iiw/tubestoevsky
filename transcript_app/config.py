"""Application configuration: .env plus CLI overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / ".env.example", override=False)

    base_url = os.getenv("LITELLM_BASE_URL", "http://127.0.0.1:4000").rstrip("/")
    api_key = os.getenv("LITELLM_API_KEY", "")
    if not api_key:
        raise SystemExit("LITELLM_API_KEY is not set: fill in .env (see .env.example)")

    return Config(
        base_url=base_url,
        api_key=api_key,
        model=model or os.getenv("LITELLM_MODEL", "glm-5-3"),
        lang=(lang or os.getenv("TRANSCRIPT_LANG", "en")).lower(),
        output_dir=Path(output_dir or os.getenv("OUTPUT_DIR", ".")).expanduser().resolve(),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
        timeout=int(os.getenv("LLM_TIMEOUT", "1800")),
        cookies=os.getenv("YTDLP_COOKIES") or None,
        cookies_from_browser=os.getenv("YTDLP_COOKIES_FROM_BROWSER") or None,
    )
