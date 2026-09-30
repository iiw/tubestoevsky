"""Output file assembly: .txt and .md."""

from __future__ import annotations

import re
from pathlib import Path


def write_txt(path: Path, title: str, prose: str) -> Path:
    header = f"{title}\nVideo transcript as prose (auto subtitles, rewritten by an LLM).\n\n"
    path.write_text(header + prose.strip() + "\n", encoding="utf-8")
    return path


def write_md(path: Path, title: str, url: str, markdown: str) -> Path:
    quote = f"> **Video transcript as prose.** Source: {url}."
    body = re.sub(r"^#.*\n+", "", markdown, flags=re.M).strip()
    content = f"# {title}\n\n{quote}\n\n---\n\n{body}\n"
    path.write_text(content, encoding="utf-8")
    return path
