"""CLI: download a transcript and turn it into prose via LangChain + an LLM API.

Example:
    uv run python -m transcript_app https://youtu.be/elj0o9QLo1g --lang en --out ../
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .chain import build_pipeline
from .config import load_config
from .downloader import SubtitlesNotFoundError, download_subtitles
from .outputs import write_md, write_txt
from .srt import srt_to_raw_text


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="transcript_app",
        description="Download a YouTube transcript and rewrite it as prose (OpenAI-compatible API + LangChain).",
    )
    parser.add_argument("url", help="video URL")
    parser.add_argument(
        "--lang",
        help="subtitle language, 2-letter locale (de, en, ...); defaults to .env TRANSCRIPT_LANG",
    )
    parser.add_argument("--out", help="output directory; defaults to .env OUTPUT_DIR")
    parser.add_argument("--model", help="model name served by the API; defaults to .env LLM_MODEL")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = load_config(lang=args.lang, output_dir=args.out, model=args.model)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] Downloading subtitles ({cfg.lang}) via yt-dlp ...")
    try:
        srt_path, _video_title = download_subtitles(
            args.url, cfg.lang, cfg.output_dir, cfg.cookies, cfg.cookies_from_browser
        )
    except SubtitlesNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"      -> {srt_path.name}")

    print("[2/4] Parsing SRT, deduplicating lines ...")
    raw = srt_to_raw_text(srt_path)
    if not raw:
        print("Error: transcript is empty", file=sys.stderr)
        return 1
    print(f"      -> {len(raw.split())} words (raw text: {len(raw)} chars)")

    print(f"[3/4] LangChain chain ({cfg.model} via {cfg.base_url}) ...")
    pipeline = build_pipeline(cfg)
    state = pipeline.invoke({"transcript": raw, "lang": cfg.lang})
    title = state.get("title") or "Transcript"
    print(f"      -> prose: {len(state['prose'].split())} words, title: \"{title}\"")

    print("[4/4] Writing .txt and .md ...")
    base = srt_path.with_suffix("")
    txt_path = write_txt(Path(f"{base}.txt"), title, state["prose"])
    md_path = write_md(Path(f"{base}.md"), title, args.url, state["markdown"])

    print("Done:")
    for p in (srt_path, txt_path, md_path):
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
