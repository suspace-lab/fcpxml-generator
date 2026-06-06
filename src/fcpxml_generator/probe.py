"""
Media file probing via ffprobe.

Extracts video metadata (fps, duration, resolution) from media files.
Used by the generator to populate accurate timing and format information
in the FCPXML output.
"""

from __future__ import annotations

import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any


class VideoInfo:
    """Metadata for a single video file."""

    __slots__ = ("path", "fps", "duration_sec", "total_frames", "width", "height")

    def __init__(
        self,
        path: str,
        fps: float = 30.0,
        duration_sec: float = 60.0,
        total_frames: int = 1800,
        width: int = 1920,
        height: int = 1080,
    ) -> None:
        self.path = path
        self.fps = fps
        self.duration_sec = duration_sec
        self.total_frames = total_frames
        self.width = width
        self.height = height


def probe_video(video_path: str) -> VideoInfo:
    """Probe a video file with ffprobe to extract metadata.

    Args:
        video_path: Absolute or relative path to the video file.

    Returns:
        VideoInfo with fps, duration, frame count, and resolution.
        Falls back to sensible defaults if probing fails.
    """
    path = Path(video_path)

    # If file doesn't exist, return defaults with a warning
    if not path.exists():
        print(f"WARNING: file not found — {video_path}", file=sys.stderr)
        return VideoInfo(path=str(path.resolve()))

    # Run ffprobe
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate,duration,nb_frames,width,height",
        "-show_entries", "format=duration",
        "-of", "json",
        str(path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffprobe error for {path.name}: {result.stderr}", file=sys.stderr)
        return VideoInfo(path=str(path.resolve()))

    try:
        data: dict[str, Any] = json.loads(result.stdout)
    except json.JSONDecodeError:
        return VideoInfo(path=str(path.resolve()))

    stream = data.get("streams", [{}])[0] if data.get("streams") else {}
    fmt = data.get("format", {})

    # Parse frame rate
    fps_str = stream.get("r_frame_rate", "30/1")
    try:
        fps = float(Fraction(fps_str))
    except (ValueError, ZeroDivisionError):
        fps = 30.0

    # Duration
    duration_sec = float(stream.get("duration") or fmt.get("duration", 60.0))

    # Frame count
    total_frames = stream.get("nb_frames")
    if total_frames is None or total_frames == "N/A":
        total_frames_int = int(round(duration_sec * fps))
    else:
        total_frames_int = int(total_frames)

    # Resolution
    width = int(stream.get("width", 1920))
    height = int(stream.get("height", 1080))

    return VideoInfo(
        path=str(path.resolve()),
        fps=fps,
        duration_sec=duration_sec,
        total_frames=total_frames_int,
        width=width,
        height=height,
    )


def probe_multiple(video_paths: list[str]) -> dict[str, VideoInfo]:
    """Probe multiple video files, returning a dict keyed by (resolved) path.

    Duplicate source paths are probed only once.
    """
    cache: dict[str, VideoInfo] = {}
    for p in video_paths:
        resolved = str(Path(p).resolve())
        if resolved not in cache:
            cache[resolved] = probe_video(p)
            print(f"  Probing: {Path(p).name}")
        # Also index by the original path for lookup convenience
        cache[p] = cache[resolved]
    return cache
