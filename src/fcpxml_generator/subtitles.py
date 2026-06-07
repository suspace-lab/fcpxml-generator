"""
SRT subtitle & title overlay generator.

Produces SRT files that can be imported into 剪映 / FCP / Premiere.
Supports both subtitles (对话字幕) and title overlays (花字/标题).

Input format (JSON):
  [
    {"start": "00:00:01,000", "end": "00:00:04,000", "text": "你好",
     "type": "subtitle"},
    {"start":    2.0,        "end":    5.0,        "text": "第一章",
     "type": "title"}
  ]

Time values accept both SRT timecode strings ("HH:MM:SS,mmm") and
float seconds. Index numbers are auto-assigned. The "type" field is
informational — all entries become SRT cues; styling is applied
inside 剪映 after import.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from typing import Any


@dataclass
class SubtitleEntry:
    """A single subtitle or title overlay cue."""
    text: str
    start_sec: float = 0.0
    end_sec: float = 3.0
    kind: str = "subtitle"  # "subtitle" | "title" — informational

    @property
    def start_srt(self) -> str:
        return _seconds_to_srt_time(self.start_sec)

    @property
    def end_srt(self) -> str:
        return _seconds_to_srt_time(self.end_sec)

    def to_srt_block(self, index: int) -> str:
        return (
            f"{index}\n"
            f"{self.start_srt} --> {self.end_srt}\n"
            f"{self.text}\n"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_srt(entries: list[dict[str, Any]]) -> str:
    """Generate a complete SRT file as a string.

    Args:
        entries: List of dicts with 'text', 'start', 'end'.
                 Optional 'type' field: "subtitle" or "title" (informational).

    Returns:
        Complete SRT file content (UTF-8).
    """
    subs = [_parse_entry(e) for e in entries]
    blocks = [sub.to_srt_block(i) for i, sub in enumerate(subs, 1)]
    return "\n".join(blocks) + "\n"


def generate_srt_file(input_path: str, output_path: str = "") -> str:
    """Read JSON subtitle entries, write SRT file. Returns output path."""
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        entries = data.get("subtitles", data.get("entries", data.get("cues", [])))
    else:
        entries = data

    if not entries:
        raise ValueError("No subtitle entries found")

    if not output_path:
        output_path = input_path.rsplit(".", 1)[0] + ".srt"

    srt_content = generate_srt(entries)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    subs = sum(1 for e in entries if e.get("type", "subtitle") == "subtitle")
    titles = sum(1 for e in entries if e.get("type", "") == "title")
    parts = [f"{len(entries)} cues"]
    if subs:
        parts.append(f"{subs} subtitles")
    if titles:
        parts.append(f"{titles} titles")

    print(f"✅ SRT generated: {output_path} ({', '.join(parts)})", file=sys.stderr)
    return output_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_entry(data: dict[str, Any]) -> SubtitleEntry:
    text = str(data.get("text", data.get("content", "")))
    start = _parse_time(data.get("start", data.get("in", 0)))
    end = _parse_time(data.get("end", data.get("out", start + 3)))
    if end <= start:
        end = start + 3.0
    return SubtitleEntry(text=text, start_sec=start, end_sec=end,
                         kind=str(data.get("type", "subtitle")))


def _parse_time(val: Any) -> float:
    """Parse float seconds or SRT timecode 'HH:MM:SS,mmm'."""
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()

    # HH:MM:SS,mmm or HH:MM:SS.mmm
    m = re.match(r"(\d+):(\d{2}):(\d{2})[,.](\d+)", s)
    if m:
        h, mn, sec, ms = m.groups()
        return int(h) * 3600 + int(mn) * 60 + int(sec) + int(ms.ljust(3, "0")[:3]) / 1000

    # HH:MM:SS (no milliseconds — check before MM:SS to avoid ambiguity)
    m = re.match(r"(\d+):(\d{2}):(\d{2})$", s)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))

    # MM:SS or MM:SS.mmm
    m = re.match(r"(\d+):(\d{2})(?:\.(\d+))?", s)
    if m:
        mn, sec = int(m.group(1)), int(m.group(2))
        ms_str = m.group(3) or "0"
        ms = int(ms_str.ljust(3, "0")[:3]) / 1000
        return mn * 60 + sec + ms

    try:
        return float(s)
    except ValueError:
        return 0.0


def _seconds_to_srt_time(seconds: float) -> str:
    """Float seconds → 'HH:MM:SS,mmm'"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")
