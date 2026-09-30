"""Subtitle download via yt-dlp: manual tracks are preferred, automatic ones
are taken in the order "<lang>-orig" (original speech) -> "<lang>".
"""

from __future__ import annotations

import re
from pathlib import Path

import yt_dlp


class SubtitlesNotFoundError(Exception):
    """No subtitles found in the requested language."""

    def __init__(self, lang: str, available: list[str]):
        self.lang = lang
        self.available = sorted(available)
        super().__init__(
            f"Subtitles '{lang}' not found. Available languages: {', '.join(self.available) or 'none'}"
        )


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|\n\r\t]", "-", name)
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    return name or "transcript"


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
    # rather than diffing the directory
    candidates = [expected] if expected.exists() else [
        p for p in out_dir.glob(f"*{sub_code}.srt")
        if sanitize_filename(video_title) in p.name
    ]
    if not candidates:
        raise RuntimeError("yt-dlp finished, but no .srt was found")

    # canonical name: sanitized title -> matching .srt/.txt/.md
    canonical = out_dir / f"{sanitize_filename(video_title)}.srt"
    srt_path = candidates[0]
    if srt_path != canonical:
        srt_path.replace(canonical)
    return canonical, video_title
