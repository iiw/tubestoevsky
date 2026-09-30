# TubeStoevsky

Downloads a YouTube video transcript and turns it into literary prose through a LangChain LLM chain served by a LiteLLM router — outputs `TXT` + `MD`.

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
cp .env.example .env   # set LITELLM_API_KEY
```

## Usage

```bash
uv run python -m transcript_app <URL>
uv run python -m transcript_app <URL> --lang en --out ./out
uv run python -m transcript_app <URL> --model deepseek-flash
```

## Configuration (`.env`)

| Variable | Purpose | Default |
|---|---|---|
| `LITELLM_BASE_URL` | LiteLLM router address | `http://127.0.0.1:4000` |
| `LITELLM_API_KEY` | router master key | **required** |
| `LITELLM_MODEL` | model name on the router | `glm-5-3` |
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
  chain.py       LangChain/LiteLLM chain
  prompts.py     step prompts
  outputs.py     .txt/.md writers
```

## Notes

- LLM steps stream: the LiteLLM proxy sometimes fails to return monolithic responses.
- `Accept-Encoding: identity` and `use_responses_api=False` work around router hangs.
- Run long requests in the foreground.
