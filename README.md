# TubeStoevsky

Downloads a YouTube video transcript and turns it into literary prose through a LangChain LLM chain — outputs `TXT` + `MD`.

Works with any OpenAI-compatible chat completions API: a local gateway, Ollama, vLLM, OpenAI, or anything else speaking that protocol.

Available on PyPI as [tubestoevsky](https://pypi.org/project/tubestoevsky/).

## How it works

```
URL
 ├─ yt-dlp       subtitles (manual > auto)  -> {title}.srt
 ├─ SRT parser   timecodes and rolling dupes -> raw text
 ├─ LangChain    prose -> title -> Markdown
 └─ output       {title}.txt, {title}.md
```

## Install

```bash
# as a CLI tool
uv tool install tubestoevsky   # or: pip install tubestoevsky
tubestoevsky --help

# from a checkout, for development
uv sync
```

## Configuration

Copy [`.env.example`](./.env.example) to `.env` and set `LLM_API_KEY`. The file
is read from the current directory, the project root, or
`~/.config/tubestoevsky/.env`.

| Variable | Purpose | Default |
|---|---|---|
| `LLM_BASE_URL` | OpenAI-compatible endpoint (`/v1` appended when absent) | `http://127.0.0.1:4000` |
| `LLM_API_KEY` | API key for that endpoint | **required** |
| `LLM_MODEL` | model name served by it | `gpt-4o-mini` |
| `TRANSCRIPT_LANG` | subtitle language | `en` |
| `OUTPUT_DIR` | output directory | `.` |
| `LLM_TEMPERATURE` | sampling temperature | `0.3` |
| `LLM_TIMEOUT` | request timeout, sec | `1800` |
| `YTDLP_COOKIES` / `YTDLP_COOKIES_FROM_BROWSER` | access to restricted videos | — |

## Usage

Install globally and run with an inline API key:

```bash
uv tool install tubestoevsky
LLM_API_KEY='sk-xxxxx' tubestoevsky --lang en --model qwen3.8-27b https://youtu.be/q0aFOxT6TNw
```

Other examples:

```bash
tubestoevsky <URL>
tubestoevsky <URL> --lang en --out ./out
tubestoevsky <URL> --model gpt-4o-mini

# or without installing:
uvx tubestoevsky <URL>

# from a checkout:
uv run python -m transcript_app <URL>
```

## Layout

```
transcript_app/
  __main__.py    CLI
  config.py      .env + CLI flags
  downloader.py  yt-dlp
  srt.py         subtitle parser
  chain.py       LangChain chain over the API
  prompts.py     step prompts
  outputs.py     .txt/.md writers
```

## Notes

- LLM steps stream: some gateways fail to return monolithic responses.
- `Accept-Encoding: identity` and `use_responses_api=False` work around proxy hangs.
- Run long requests in the foreground.
