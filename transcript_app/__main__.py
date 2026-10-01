"""CLI: download a transcript and turn it into prose via LangChain + an LLM API.

Example:
    uv run python -m transcript_app https://youtu.be/elj0o9QLo1g --lang en --out ../
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .chain import build_pipeline
from .config import (
    CONFIG_KEYS,
    _read_env_files,
    _resolve_setting,
    load_config,
    read_saved_config,
    write_saved_config,
)
from .downloader import SubtitlesNotFoundError, download_subtitles
from .outputs import write_md, write_txt
from .srt import srt_to_raw_text
from .version import __version__


def _build_parser() -> argparse.ArgumentParser:
    config_keys = ", ".join(CONFIG_KEYS)
    parser = argparse.ArgumentParser(
        prog="tubestoevsky",
        description="Download a YouTube transcript and rewrite it as prose (OpenAI-compatible API + LangChain).",
        epilog="Run `tubestoevsky run URL` (or `tubestoevsky URL`) for the default action. Precedence: environment variables override ~/.tubestoevsky/config.yaml; direct CLI flags override both.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    config = commands.add_parser(
        "config",
        help="manage persistent settings in ~/.tubestoevsky/config.yaml",
        description="Manage persistent settings in ~/.tubestoevsky/config.yaml. Environment variables always override these settings.",
    )
    config_subcommands = config.add_subparsers(dest="config_command", metavar="ACTION")

    set_config = config_subcommands.add_parser(
        "set",
        help="set a configuration value",
        description=f"Set a persistent configuration value. Keys: {config_keys}.",
    )
    set_config.add_argument("key", choices=CONFIG_KEYS, help="configuration key")
    set_config.add_argument("value", help="configuration value")

    get_config = config_subcommands.add_parser(
        "get",
        help="get a configuration value",
        description=f"Get a configuration value. Keys: {config_keys}.",
    )
    get_config.add_argument(
        "key",
        choices=CONFIG_KEYS,
        help="configuration key",
    )
    get_config.add_argument(
        "--show-source",
        action="store_true",
        help="show whether the value comes from environment, config, or default",
    )

    run = commands.add_parser(
        "run",
        help="download a transcript and rewrite it (default command)",
        description="Download a YouTube transcript and rewrite it as prose.",
    )
    run.add_argument("url", help="video URL")
    run.add_argument(
        "--lang",
        help="subtitle language (2-letter locale); overrides TRANSCRIPT_LANG",
    )
    run.add_argument(
        "--out",
        help="output directory; overrides OUTPUT_DIR",
    )
    run.add_argument(
        "--model",
        help="model name served by the API; overrides LLM_MODEL",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return _build_parser().parse_args(argv)


def _config_get(args: argparse.Namespace) -> int:
    saved = read_saved_config()
    value, source = _resolve_setting(
        args.key,
        saved,
        _read_env_files(),
    )
    print(f"{value}\t{source}" if args.show_source else value)
    return 0


def _config_set(args: argparse.Namespace) -> int:
    saved = read_saved_config()
    saved[args.key] = args.value
    path = write_saved_config(saved)
    print(f"Saved {args.key} to {path}")
    return 0


def _run(args: argparse.Namespace) -> int:
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
    print(f'      -> prose: {len(state["prose"].split())} words, title: "{title}"')

    print("[4/4] Writing .txt and .md ...")
    base = srt_path.with_suffix("")
    txt_path = write_txt(Path(f"{base}.txt"), title, state["prose"])
    md_path = write_md(Path(f"{base}.md"), title, args.url, state["markdown"])

    print("Done:")
    for p in (srt_path, txt_path, md_path):
        print(f"  {p}")
    return 0


def main(argv: list[str] | None = None) -> int:
    tokens = list(argv) if argv is not None else list(sys.argv[1:])
    # Preserve the original invocation without an explicit `run` command.
    if not tokens or tokens[0] not in {"config", "run", "-h", "--help", "--version"}:
        tokens.insert(0, "run")
    args = parse_args(tokens)

    if args.command == "config":
        if args.config_command == "set":
            return _config_set(args)
        if args.config_command == "get":
            return _config_get(args)
        raise SystemExit(_build_parser().format_help())
    if args.command == "run":
        return _run(args)
    raise AssertionError(f"unhandled command: {args.command!r}")


if __name__ == "__main__":
    raise SystemExit(main())
