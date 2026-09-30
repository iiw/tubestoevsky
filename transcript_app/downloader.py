"""Subtitle download via yt-dlp: manual tracks are preferred, automatic ones
are taken in the order "<lang>-orig" (original speech) -> "<lang>".
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import yt_dlp

# Device names that Windows still reserves, with or without an extension.
_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}

# Most filesystems cap a single name at 255 bytes; leave room for ".120.srt".
_MAX_BASENAME_BYTES = 200


class SubtitlesNotFoundError(Exception):
    """No subtitles found in the requested language."""

    def __init__(self, lang: str, available: list[str]):
        self.lang = lang
        self.available = sorted(available)
        super().__init__(
            f"Subtitles '{lang}' not found. Available languages: {', '.join(self.available) or 'none'}"
        )


def sanitize_filename(name: str) -> str:
    """Return a filesystem- and URL-safe basename.

    Keeps Unicode letters, digits, ASCII hyphen, underscore, and dot.
    Spaces become hyphens; all other characters are replaced with hyphens.
    """
    normalized = unicodedata.normalize("NFKC", name)
    cleaned: list[str] = []
    for char in normalized:
        if char.isalnum() or char in "._-":
            cleaned.append(char)
        else:
            cleaned.append("-")
    name = "".join(cleaned)
    name = re.sub(r"-{2,}", "-", name).strip("-._")
    # "NUL" and "NUL.txt" are both reserved on Windows, so check the stem.
    if name.split(".", 1)[0].upper() in _WINDOWS_RESERVED:
        name = f"{name}-file"

    if len(name.encode("utf-8")) > _MAX_BASENAME_BYTES:
        name = _truncate_bytes(name, _MAX_BASENAME_BYTES).strip("-._")
    return name or "transcript"


def _truncate_bytes(name: str, limit: int) -> str:
    """Cut a string at a UTF-8 byte budget without splitting a character."""
    encoded = name.encode("utf-8")[:limit]
    return encoded.decode("utf-8", errors="ignore")


def _yt_options(**extra: dict) -> dict:
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    opts.update(extra)
    return opts


def _cookie_options(cfg_cookies: str | None, cfg_browser: str | None) -> dict:
    opts: dict = {}
    if cfg_cookies:
        opts["cookiefile"] = cfg_cookies
    if cfg_browser:
        opts["cookiesfrombrowser"] = (cfg_browser,)
    return opts


def _extract_info(url: str, cookies: str | None = None, cookies_from_browser: str | None = None) -> dict:
    opts = _yt_options(**_cookie_options(cookies, cookies_from_browser))
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def _pick_subtitle(info: dict, lang: str) -> tuple[str, bool] | None:
    """Return (track code, is_manual) or None."""
    manual = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}

    if lang in manual:
        return lang, True
    if f"{lang}-orig" in manual:
        return f"{lang}-orig", True

    for code in (f"{lang}-orig", lang):
        if code in auto:
            return code, False
    return None


def download_subtitles(
    url: str, lang: str, out_dir: Path, cookies: str | None = None, cookies_from_browser: str | None = None
) -> tuple[Path, str]:
    """Download subtitles as .srt into out_dir.

    Returns (path to the .srt, verbatim video title).
    """
    info = _extract_info(url, cookies, cookies_from_browser)
    video_title: str = info.get("title") or "transcript"

    picked = _pick_subtitle(info, lang)
    if picked is None:
        available = set(info.get("subtitles") or {}) | set(info.get("automatic_captions") or {})
        raise SubtitlesNotFoundError(lang, available)
    sub_code, is_manual = picked

    out_dir.mkdir(parents=True, exist_ok=True)
    opts = _yt_options(
        **_cookie_options(cookies, cookies_from_browser),
        subtitleslangs=[sub_code],
        subtitlesformat="srt/best",
        outtmpl={"default": str(out_dir / "%(title)s.%(ext)s")},
    )
    if is_manual:
        opts["writesubtitles"] = True
    else:
        opts["writeautomaticsub"] = True

    # expected subtitle name: base + ".<code>.srt" (yt-dlp sanitizes the title itself)
    with yt_dlp.YoutubeDL(opts) as ydl:
        base = Path(ydl.prepare_filename(info)).with_suffix("")
        expected = out_dir / f"{base.name}.{sub_code}.srt"
        ydl.download([url])

    # yt-dlp may overwrite an existing file, so look for the expected name
    # rather than diffing the directory. Compare sanitized stems, because
    # yt-dlp's own title sanitization differs from ours.
    stem = sanitize_filename(video_title)
    suffix = f".{sub_code}.srt"
    candidates = [expected] if expected.exists() else [
        path
        for path in sorted(out_dir.glob(f"*{suffix}"))
        if sanitize_filename(path.name.removesuffix(suffix)) == stem
    ]
    if not candidates:
        raise RuntimeError("yt-dlp finished, but no .srt was found")

    # canonical name: sanitized title -> matching .srt/.txt/.md
    canonical = out_dir / f"{stem}.srt"
    srt_path = candidates[0]
    if srt_path != canonical:
        srt_path.replace(canonical)
    return canonical, video_title
