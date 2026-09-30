# TubeStoevsky

Downloads a YouTube video transcript and turns it into literary prose through a LangChain LLM chain — outputs `TXT` + `MD`.

Works with any OpenAI-compatible chat completions API: a local gateway, Ollama, vLLM, OpenAI, or anything else speaking that protocol.

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
uv sync
cp .env.example .env   # set LLM_API_KEY
```

## Usage

```bash
uv run python -m transcript_app <URL>
uv run python -m transcript_app <URL> --lang en --out ./out
uv run python -m transcript_app <URL> --model gpt-4o-mini
```

## Configuration (`.env`)

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
