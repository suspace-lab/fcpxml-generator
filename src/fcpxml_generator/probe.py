"""
Media file probing via ffprobe.

Extracts video/audio metadata (fps, duration, resolution, codec info)
from media files. Handles video-only, audio-only, and mixed files.
"""

from __future__ import annotations

import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any


class MediaInfo:
    """Metadata for a single media file (video or audio)."""

    __slots__ = (
        "path", "fps", "duration_sec", "total_frames",
        "width", "height", "has_video", "has_audio",
    )

    def __init__(
        self,
        path: str,
        fps: float = 30.0,
        duration_sec: float = 60.0,
        total_frames: int = 1800,
        width: int = 1920,
        height: int = 1080,
        has_video: bool = True,
        has_audio: bool = True,
    ) -> None:
        self.path = path
        self.fps = fps
        self.duration_sec = duration_sec
        self.total_frames = total_frames
        self.width = width
        self.height = height
        self.has_video = has_video
        self.has_audio = has_audio

    @property
    def is_audio_only(self) -> bool:
        return self.has_audio and not self.has_video

    @property
    def is_video_only(self) -> bool:
        return self.has_video and not self.has_audio


# Backward-compatible alias
VideoInfo = MediaInfo


def probe_media(media_path: str) -> MediaInfo:
    """Probe a media file with ffprobe to extract metadata.

    Detects video-only, audio-only, and mixed files automatically.
    Falls back to sensible defaults if probing fails.

    Args:
        media_path: Absolute or relative path to the media file.

    Returns:
        MediaInfo with fps, duration, resolution, and stream flags.
    """
    path = Path(media_path)

    if not path.exists():
        print(f"WARNING: file not found — {media_path}", file=sys.stderr)
        return MediaInfo(path=str(path.resolve()))

    # Probe all streams at once
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_type,r_frame_rate,duration,nb_frames,width,height",
        "-show_entries", "format=duration",
        "-of", "json",
        str(path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffprobe error for {path.name}: {result.stderr}", file=sys.stderr)
        return MediaInfo(path=str(path.resolve()))

    try:
        data: dict[str, Any] = json.loads(result.stdout)
    except json.JSONDecodeError:
        return MediaInfo(path=str(path.resolve()))

    streams: list[dict[str, Any]] = data.get("streams", [])
    fmt: dict[str, Any] = data.get("format", {})

    # Separate video and audio streams
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    has_video = len(video_streams) > 0
    has_audio = len(audio_streams) > 0

    # Defaults
    fps = 30.0
    width = 1920
    height = 1080
    total_frames = 0

    # Extract video info if present
    if has_video:
        vs = video_streams[0]
        fps_str = vs.get("r_frame_rate", "30/1")
        try:
            fps = float(Fraction(fps_str))
        except (ValueError, ZeroDivisionError):
            fps = 30.0
        width = int(vs.get("width", 1920))
        height = int(vs.get("height", 1080))
        total_frames = vs.get("nb_frames")
    else:
        # Audio-only: use default resolution, fps doesn't matter much
        fps = 30.0
        width = 0
        height = 0

    # Duration — prefer stream duration, fall back to format duration
    duration_sec = 60.0
    for s in streams:
        if s.get("duration"):
            duration_sec = float(s["duration"])
            break
    if duration_sec == 60.0 and fmt.get("duration"):
        duration_sec = float(fmt["duration"])

    # Frame count fallback
    if total_frames is None or total_frames == "N/A" or total_frames == 0:
        total_frames_int = int(round(duration_sec * fps)) if has_video else 0
    else:
        total_frames_int = int(total_frames)

    return MediaInfo(
        path=str(path.resolve()),
        fps=fps,
        duration_sec=duration_sec,
        total_frames=total_frames_int,
        width=width,
        height=height,
        has_video=has_video,
        has_audio=has_audio,
    )


# Backward-compatible alias
probe_video = probe_media


def probe_multiple(media_paths: list[str]) -> dict[str, MediaInfo]:
    """Probe multiple media files, returning a dict keyed by path.

    Duplicate source paths are probed only once. Both resolved and
    original paths are indexed for convenience.
    """
    cache: dict[str, MediaInfo] = {}
    for p in media_paths:
        resolved = str(Path(p).resolve())
        if resolved not in cache:
            cache[resolved] = probe_media(p)
            info = cache[resolved]
            tag = ""
            if info.is_audio_only:
                tag = " [audio-only]"
            elif info.is_video_only:
                tag = " [video-only]"
            print(f"  Probing: {Path(p).name}{tag}")
        cache[p] = cache[resolved]
    return cache
