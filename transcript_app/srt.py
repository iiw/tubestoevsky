"""SRT parser: extract text and deduplicate the "rolling" lines of automatic
subtitles (each line repeats the previous one with an addition).
"""

from __future__ import annotations

import re
from pathlib import Path


def srt_to_raw_text(srt_path: Path) -> str:
    """SRT -> plain cleaned text without timecodes or duplicates."""
    text = srt_path.read_text(encoding="utf-8", errors="replace")
    events: list[str] = []

    for block in re.split(r"\n\s*\n", text):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        body = " ".join(
            ln for ln in lines if "-->" not in ln and not re.fullmatch(r"\d+", ln)
        )
        body = re.sub(r"\s+", " ", body).strip()
        if body:
            events.append(body)

    deduped: list[str] = []
    for ev in events:
        if deduped and (ev == deduped[-1] or (deduped[-1] in ev and len(ev) > len(deduped[-1]))):
            deduped[-1] = ev
        else:
            deduped.append(ev)

    raw = " ".join(deduped)
    raw = re.sub(r"\s+([,.!?;:])", r"\1", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw
