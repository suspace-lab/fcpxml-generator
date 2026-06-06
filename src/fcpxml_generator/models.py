"""
Data models for the edit script and FCPXML generation.

Defines the canonical JSON schema that AI agents produce,
with validation, backward compatibility, and a clean API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional, Union


# ---------------------------------------------------------------------------
# Timeline item types
# ---------------------------------------------------------------------------

@dataclass
class ClipItem:
    """A video or audio clip on the timeline.

    Source attributes:
        source: Absolute path to the media file.
        in_sec: In-point in seconds within the source file.
        out_sec: Out-point in seconds within the source file.
    """
    source: str
    in_sec: float = 0.0
    out_sec: float = 3.0
    filename: str = ""
    transition: str = "cut"

    # Metadata (informational, not written to FCPXML)
    description: str = ""
    dialogue: str = ""

    @property
    def duration_sec(self) -> float:
        return max(self.out_sec - self.in_sec, 0.0)


@dataclass
class GapItem:
    """A blank gap / spacer on the timeline."""
    duration_sec: float = 1.0


# A track item is either a clip or a gap
TrackItem = Union[ClipItem, GapItem]


@dataclass
class Track:
    """A video or audio track containing clips and gaps."""
    name: str = "V1"
    role: Literal["video", "audio"] = "video"
    items: list[TrackItem] = field(default_factory=list)


@dataclass
class Marker:
    """A marker (chapter or annotation) on the timeline."""
    name: str
    time_sec: float = 0.0
    color: str = "Red"  # FCPXML marker colors


@dataclass
class EditScript:
    """Complete edit script — the canonical input to fcpxml-generator.

    This is what AI agents produce. It can be serialized to/from JSON.
    """

    title: str = "Untitled Project"
    fps: Optional[float] = None          # Auto-detected if None
    resolution: Optional[str] = None      # "WxH", auto-detected if None
    tracks: list[Track] = field(default_factory=list)
    markers: list[Marker] = field(default_factory=list)

    # Legacy fields for backward compatibility
    music_mood: str = ""
    total_duration: str = ""

    @property
    def all_clip_sources(self) -> list[str]:
        """Return deduplicated list of all source file paths."""
        sources: list[str] = []
        seen: set[str] = set()
        for track in self.tracks:
            for item in track.items:
                if isinstance(item, ClipItem) and item.source not in seen:
                    sources.append(item.source)
                    seen.add(item.source)
        return sources

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict (the edit_script.json format)."""
        d: dict = {
            "title": self.title,
            "tracks": [
                {
                    "name": t.name,
                    "role": t.role,
                    "items": [
                        self._item_to_dict(it) for it in t.items
                    ],
                }
                for t in self.tracks
            ],
        }
        if self.fps is not None:
            d["fps"] = self.fps
        if self.resolution is not None:
            d["resolution"] = self.resolution
        if self.markers:
            d["markers"] = [
                {"name": m.name, "time": f"{m.time_sec:.2f}", "color": m.color}
                for m in self.markers
            ]
        if self.music_mood:
            d["music_mood"] = self.music_mood
        if self.total_duration:
            d["total_duration"] = self.total_duration
        return d

    @staticmethod
    def _item_to_dict(item: TrackItem) -> dict:
        if isinstance(item, ClipItem):
            d: dict = {
                "type": "clip",
                "source": item.source,
                "in": item.in_sec,
                "out": item.out_sec,
            }
            if item.filename:
                d["filename"] = item.filename
            if item.transition and item.transition != "cut":
                d["transition"] = item.transition
            if item.description:
                d["description"] = item.description
            if item.dialogue:
                d["dialogue"] = item.dialogue
            return d
        else:
            return {
                "type": "gap",
                "duration": item.duration_sec,
            }

    # ------------------------------------------------------------------
    # Deserialization (from old and new formats)
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict) -> EditScript:
        """Parse from a JSON dict.

        Supports both:
        - New format: {"tracks": [{"name": "V1", "role": "video", "items": [...]}]}
        - Old format: {"clips": [{"source": "...", "in": "00:00", "out": "00:13"}]}
        """
        title = data.get("title", "Untitled Project")
        fps = data.get("fps")
        resolution = data.get("resolution")
        music_mood = data.get("music_mood", "")
        total_duration = data.get("total_duration", "")

        tracks: list[Track] = []

        # New format: explicit tracks
        if "tracks" in data:
            for t_data in data["tracks"]:
                track = Track(
                    name=t_data.get("name", "V1"),
                    role=t_data.get("role", "video"),
                )
                for it_data in t_data.get("items", []):
                    item = cls._parse_item(it_data)
                    if item:
                        track.items.append(item)
                tracks.append(track)

        # Old format: flat clips list (backward compat)
        elif "clips" in data:
            track = Track(name="V1", role="video")
            for c_data in data["clips"]:
                clip = ClipItem(
                    source=c_data.get("source", ""),
                    in_sec=parse_timecode_float(c_data.get("in", "00:00")),
                    out_sec=parse_timecode_float(c_data.get("out", "00:00")),
                    filename=c_data.get("filename", ""),
                    transition=c_data.get("transition", "cut"),
                    description=c_data.get("description", ""),
                    dialogue=c_data.get("dialogue", ""),
                )
                track.items.append(clip)
            tracks.append(track)

        # Markers
        markers: list[Marker] = []
        for m_data in data.get("markers", []):
            markers.append(Marker(
                name=m_data.get("name", ""),
                time_sec=_parse_marker_time(m_data.get("time", "0")),
                color=m_data.get("color", "Red"),
            ))

        return cls(
            title=title,
            fps=fps,
            resolution=resolution,
            tracks=tracks,
            markers=markers,
            music_mood=music_mood,
            total_duration=total_duration,
        )

    @staticmethod
    def _parse_item(data: dict) -> TrackItem | None:
        itype = data.get("type", "clip")
        if itype == "gap":
            dur = data.get("duration", 1.0)
            if isinstance(dur, str):
                dur = parse_timecode_float(dur)
            return GapItem(duration_sec=float(dur))
        else:
            # clip
            in_val = data.get("in", 0)
            out_val = data.get("out", 3)
            if isinstance(in_val, str):
                in_val = parse_timecode_float(in_val)
            if isinstance(out_val, str):
                out_val = parse_timecode_float(out_val)
            return ClipItem(
                source=data.get("source", ""),
                in_sec=float(in_val),
                out_sec=float(out_val),
                filename=data.get("filename", ""),
                transition=data.get("transition", "cut"),
                description=data.get("description", ""),
                dialogue=data.get("dialogue", ""),
            )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@dataclass
class ValidationError:
    """A single validation issue."""
    path: str          # e.g. "tracks[0].items[2].source"
    message: str
    severity: Literal["error", "warning"] = "error"


def validate_script(script: EditScript) -> list[ValidationError]:
    """Validate an edit script and return all issues found.

    Checks:
      - At least one track with at least one clip
      - All clip sources are non-empty
      - All clips have valid in/out (out > in)
      - Gaps have positive duration
      - Marker times are non-negative
    """
    errors: list[ValidationError] = []

    if not script.tracks:
        errors.append(ValidationError("tracks", "At least one track is required"))
        return errors

    has_any_clip = False

    for ti, track in enumerate(script.tracks):
        if not track.items:
            errors.append(ValidationError(
                f"tracks[{ti}].items",
                f"Track '{track.name}' has no items",
                "warning",
            ))
            continue

        for ii, item in enumerate(track.items):
            base = f"tracks[{ti}].items[{ii}]"

            if isinstance(item, ClipItem):
                has_any_clip = True
                if not item.source:
                    errors.append(ValidationError(f"{base}.source", "Source path is empty"))
                if item.out_sec <= item.in_sec:
                    errors.append(ValidationError(
                        f"{base}",
                        f"out ({item.out_sec:.2f}s) must be > in ({item.in_sec:.2f}s)",
                    ))
            elif isinstance(item, GapItem):
                if item.duration_sec <= 0:
                    errors.append(ValidationError(
                        f"{base}.duration",
                        f"Gap duration must be positive, got {item.duration_sec}",
                    ))

    if not has_any_clip:
        errors.append(ValidationError("tracks", "No clips found — at least one clip is required"))

    for mi, marker in enumerate(script.markers):
        if marker.time_sec < 0:
            errors.append(ValidationError(
                f"markers[{mi}].time",
                f"Marker time must be >= 0, got {marker.time_sec}",
            ))
        if not marker.name:
            errors.append(ValidationError(
                f"markers[{mi}].name",
                "Marker name is empty",
                "warning",
            ))

    return errors


# ---------------------------------------------------------------------------
# Timecode parsing helpers (shared with timecode.py)
# ---------------------------------------------------------------------------

def parse_timecode_float(tc: str | float | int) -> float:
    """Parse a timecode or time value to seconds (float).

    Accepts:
        "MM:SS", "HH:MM:SS", "MM:SS.mmm"
        float (already in seconds) → pass through
    """
    if isinstance(tc, (float, int)):
        return float(tc)
    tc = str(tc).strip()
    parts = tc.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    try:
        return float(tc)
    except ValueError:
        return 0.0


def _parse_marker_time(val: str | float | int) -> float:
    """Parse marker time value (seconds or timecode)."""
    if isinstance(val, (float, int)):
        return float(val)
    return parse_timecode_float(val)
