"""
Core FCPXML 1.9 document generator.

Takes an EditScript and produces a valid FCPXML document conforming to
the Apple FCPXML 1.9 specification. Supports:

  - Multi-track video + audio timelines
  - Secondary video tracks → <connected-clip> (B-roll / overlay)
  - Audio tracks → <asset-clip> in <audio> lane
  - Gaps / spacers between clips
  - Chapter / annotation markers
  - Audio-only clips (music, voiceover — hasVideo="0")
  - Backward-compatible flat "clips" format
  - <media-rep> in every <asset> (required by spec)
  - "0s" for zero-value time attributes (not "0/30000s")
"""

from __future__ import annotations

import io
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .models import (
    ClipItem,
    EditScript,
    GapItem,
    Marker,
    Track,
    TrackItem,
)
from .probe import MediaInfo, probe_multiple
from .timecode import (
    FrameRate,
    detect_frame_rate,
    fcpxml_format_name,
    resolve_frame_rate,
    seconds_to_fcpxml,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_fcpxml(
    edit_script: dict[str, Any] | EditScript,
    *,
    media_dir: str = "",
    override_fps: str | None = None,
    override_resolution: str | None = None,
) -> str:
    """Generate a complete FCPXML 1.9 document string.

    Accepts either an EditScript object or a raw JSON dict (backward compat).

    Returns a complete FCPXML 1.9 document as a UTF-8 string.
    """
    if isinstance(edit_script, dict):
        script = EditScript.from_dict(edit_script)
    else:
        script = edit_script

    if not script.tracks:
        raise ValueError("edit_script has no tracks — nothing to generate")

    # ------------------------------------------------------------------
    # 1. Probe all unique sources
    # ------------------------------------------------------------------
    unique_sources = script.all_clip_sources
    if not unique_sources:
        raise ValueError("No clips with valid 'source' paths found")

    info_cache = probe_multiple(unique_sources)

    # ------------------------------------------------------------------
    # 2. Determine frame rate & resolution
    # ------------------------------------------------------------------
    common_fr = _resolve_frame_rate(script, unique_sources, info_cache, override_fps)
    width, height = _resolve_resolution(script, unique_sources, info_cache, override_resolution)
    format_name = fcpxml_format_name(width, height, common_fr)

    print(f"  Timeline: {width}x{height} @ {common_fr.fps:.4f} fps", file=sys.stderr)

    # ------------------------------------------------------------------
    # 3. Build FCPXML document tree
    # ------------------------------------------------------------------
    root = ET.Element("fcpxml", {"version": "1.9"})
    resources = ET.SubElement(root, "resources")

    # Format
    ET.SubElement(resources, "format", {
        "id": "r0",
        "name": format_name,
        "frameDuration": common_fr.frame_duration,
        "width": str(width),
        "height": str(height),
    })

    # Assets (one per unique source, with correct hasVideo/hasAudio flags)
    asset_ids = _build_assets(resources, unique_sources, info_cache, common_fr)

    # Library / Event / Project / Sequence
    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event", {"name": script.title})
    project = ET.SubElement(event, "project", {"name": script.title})
    sequence = ET.SubElement(project, "sequence", {
        "format": "r0",
        "duration": "0s",
        "tcStart": "0s",
        "tcFormat": "NDF",
        "audioLayout": "stereo",
        "audioRate": "48k",
    })

    # Separate tracks
    video_tracks = [t for t in script.tracks if t.role == "video"]
    audio_tracks = [t for t in script.tracks if t.role == "audio"]

    if not video_tracks and not audio_tracks:
        raise ValueError("No video or audio tracks found")

    # Primary storyline: first video track → spine
    spine = ET.SubElement(sequence, "spine")

    if video_tracks:
        _build_track_items(spine, video_tracks[0].items, asset_ids, common_fr, "spine")
    else:
        # Audio-only timeline: first audio track → spine
        _build_track_items(spine, audio_tracks[0].items, asset_ids, common_fr, "spine")
        audio_tracks = audio_tracks[1:]

    # Secondary video tracks → <connected-clip> inside the spine
    for vtrack in video_tracks[1:]:
        _build_connected_clips(spine, vtrack.items, asset_ids, common_fr, vtrack.name)

    # Audio tracks → <asset-clip> directly in sequence (FCPXML audio lanes)
    for atrack in audio_tracks:
        _build_audio_lane(sequence, atrack.items, asset_ids, common_fr, atrack.name)

    # Markers
    for marker in script.markers:
        _build_marker(sequence, marker, common_fr)

    # ------------------------------------------------------------------
    # 4. Serialize
    # ------------------------------------------------------------------
    ET.indent(root, space="  ")

    buf = io.BytesIO()
    buf.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    tree = ET.ElementTree(root)
    tree.write(buf, encoding="utf-8", xml_declaration=False)
    return buf.getvalue().decode("utf-8") + "\n"


def generate_fcpxml_file(
    edit_script_path: str,
    output_path: str = "",
    *,
    media_dir: str = "",
    override_fps: str | None = None,
    override_resolution: str | None = None,
    dry_run: bool = False,
) -> str:
    """Read edit_script JSON, generate FCPXML, write to file.

    Returns the output file path.
    """
    with open(edit_script_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if not output_path:
        title = raw.get("title", "untitled")
        output_path = f"{title.replace(' ', '_').replace('-', '_')}.fcpxml"

    if dry_run:
        return _dry_run(raw, output_path)

    xml_string = generate_fcpxml(
        raw,
        media_dir=media_dir,
        override_fps=override_fps,
        override_resolution=override_resolution,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_string)

    print(f"\n✅ FCPXML generated: {output_path}", file=sys.stderr)
    print(f"   Import: 剪映专业版 → 导入工程 → 选择此文件", file=sys.stderr)
    return output_path


# ---------------------------------------------------------------------------
# Dry-run preview
# ---------------------------------------------------------------------------

def _dry_run(raw: dict[str, Any], output_path: str) -> str:
    """Preview the timeline without generating FCPXML."""
    from .models import EditScript as ES
    script = ES.from_dict(raw)

    # Probe sources
    sources = script.all_clip_sources
    info_cache = probe_multiple(sources) if sources else {}

    print(f"\n{'─' * 60}")
    print(f"  DRY RUN — preview only, no file written")
    print(f"{'─' * 60}")
    print(f"  Title:    {script.title}")
    print(f"  Output:   {output_path} (would be written)")

    total_clips = 0
    total_gaps = 0
    total_dur = 0.0

    for track in script.tracks:
        clips = [i for i in track.items if isinstance(i, ClipItem)]
        gaps = [i for i in track.items if isinstance(i, GapItem)]
        dur = sum(
            (c.out_sec - c.in_sec) if isinstance(c, ClipItem)
            else c.duration_sec if isinstance(c, GapItem)
            else 0
            for c in track.items
        )
        total_clips += len(clips)
        total_gaps += len(gaps)
        total_dur += dur

        audio_only = [c for c in clips if info_cache.get(c.source) and info_cache[c.source].is_audio_only]
        print(f"\n  Track: {track.name} ({track.role})")
        print(f"    Items: {len(track.items)} ({len(clips)} clips, {len(gaps)} gaps)")
        print(f"    Duration: {dur:.1f}s")
        if audio_only:
            print(f"    Audio-only clips: {len(audio_only)}")

    print(f"\n  Total clips:  {total_clips}")
    print(f"  Total gaps:   {total_gaps}")
    print(f"  Est. duration: {total_dur:.1f}s ({total_dur/60:.1f} min)")
    print(f"  Tracks:       {len(script.tracks)}")
    print(f"  Markers:      {len(script.markers)}")
    print(f"{'─' * 60}")

    return output_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_frame_rate(
    script: EditScript,
    sources: list[str],
    info_cache: dict[str, MediaInfo],
    override_fps: str | None,
) -> FrameRate:
    if override_fps:
        return resolve_frame_rate(override_fps)
    if script.fps is not None:
        return detect_frame_rate(script.fps)

    fps_votes: dict[str, int] = {}
    for src in sources:
        info = info_cache.get(src)
        if info and info.has_video:
            fr = detect_frame_rate(info.fps)
            key = f"{fr.fps:.4f}"
            fps_votes[key] = fps_votes.get(key, 0) + 1
    if fps_votes:
        best_key = max(fps_votes, key=fps_votes.get)
        return resolve_frame_rate(best_key)
    return resolve_frame_rate("30")


def _resolve_resolution(
    script: EditScript,
    sources: list[str],
    info_cache: dict[str, MediaInfo],
    override_resolution: str | None,
) -> tuple[int, int]:
    if override_resolution:
        w, h = override_resolution.split("x")
        return int(w), int(h)
    if script.resolution:
        w, h = script.resolution.split("x")
        return int(w), int(h)

    # Find first video source with actual resolution
    for src in sources:
        info = info_cache.get(src)
        if info and info.has_video and info.width > 0:
            return info.width, info.height
    return 1920, 1080


def _build_assets(
    resources: ET.Element,
    sources: list[str],
    info_cache: dict[str, MediaInfo],
    common_fr: FrameRate,
) -> dict[str, str]:
    """Build <asset> elements with correct hasVideo/hasAudio flags."""
    asset_ids: dict[str, str] = {}
    for i, src in enumerate(sources, 1):
        asset_id = f"r{i}"
        asset_ids[src] = asset_id
        info = info_cache.get(src)

        file_fr = detect_frame_rate(info.fps) if info and info.has_video else common_fr
        dur_tc = seconds_to_fcpxml(info.duration_sec, file_fr) if info and info.duration_sec > 0 else "60s"

        abs_path = os.path.abspath(src)
        # URL-encode properly (handles spaces, Chinese chars, etc.)
        file_url = Path(abs_path).as_uri()
        file_name = Path(src).name

        # Per-source flags: auto-detect from probe, no per-clip override at asset level
        has_v = "1" if (info.has_video if info else True) else "0"
        has_a = "1" if (info.has_audio if info else True) else "0"

        # Audio-only files don't need format reference
        asset_attrs: dict[str, str] = {
            "id": asset_id,
            "name": file_name,
            "src": file_url,
            "start": "0s",
            "duration": dur_tc,
            "hasVideo": has_v,
            "hasAudio": has_a,
        }
        if has_v == "1":
            asset_attrs["format"] = "r0"
        if has_a == "1":
            asset_attrs["audioSources"] = "1"
            asset_attrs["audioChannels"] = "2"

        asset = ET.SubElement(resources, "asset", asset_attrs)

        ET.SubElement(asset, "media-rep", {
            "kind": "original-media",
            "src": file_url,
        })
    return asset_ids


def _build_track_items(
    parent: ET.Element,
    items: list[TrackItem],
    asset_ids: dict[str, str],
    common_fr: FrameRate,
    label: str,
) -> None:
    """Build <asset-clip> and <gap> elements on a parent (spine or audio lane)."""
    current_offset: float = 0.0
    clip_count = 0

    for item in items:
        if isinstance(item, GapItem):
            dur = max(item.duration_sec, 0.0)
            ET.SubElement(parent, "gap", {
                "name": "Gap",
                "offset": seconds_to_fcpxml(current_offset, common_fr),
                "duration": seconds_to_fcpxml(dur, common_fr),
            })
            current_offset += dur

        elif isinstance(item, ClipItem):
            clip_count += 1
            source = item.source
            filename = item.filename or (Path(source).name if source else f"clip_{clip_count}")
            in_sec = item.in_sec
            out_sec = item.out_sec
            if out_sec <= in_sec:
                out_sec = in_sec + 3.0
            dur_sec = out_sec - in_sec
            aid = asset_ids.get(source, "r1")

            ET.SubElement(parent, "asset-clip", {
                "name": filename,
                "ref": aid,
                "offset": seconds_to_fcpxml(current_offset, common_fr),
                "duration": seconds_to_fcpxml(dur_sec, common_fr),
                "start": seconds_to_fcpxml(in_sec, common_fr),
                "tcFormat": "NDF",
            })

            print(
                f"  [{label}] {clip_count:2d}. {filename[:30]:30s}  "
                f"offset={seconds_to_fcpxml(current_offset, common_fr):>16s}  "
                f"start={seconds_to_fcpxml(in_sec, common_fr):>16s}  "
                f"dur={seconds_to_fcpxml(dur_sec, common_fr):>16s}",
                file=sys.stderr,
            )
            current_offset += dur_sec


def _build_connected_clips(
    spine: ET.Element,
    items: list[TrackItem],
    asset_ids: dict[str, str],
    common_fr: FrameRate,
    track_name: str,
) -> None:
    """Build secondary video track items as <connected-clip> elements.

    Connected clips overlay the primary storyline (B-roll, cutaways, etc.).
    They are placed as children of <asset-clip> elements in the spine.
    """
    clip_items = [it for it in items if isinstance(it, ClipItem)]
    if not clip_items:
        return

    # Find the first spine asset-clip to attach connected clips to
    spine_clips = spine.findall("asset-clip")
    if not spine_clips:
        return

    # For simplicity, attach all connected clips to the first spine clip
    # with offsets calculated from timeline start
    current_offset: float = 0.0
    count = 0

    for item in items:
        if isinstance(item, ClipItem):
            count += 1
            source = item.source
            filename = item.filename or Path(source).name
            in_sec = item.in_sec
            out_sec = item.out_sec
            if out_sec <= in_sec:
                out_sec = in_sec + 3.0
            dur_sec = out_sec - in_sec
            aid = asset_ids.get(source, "r1")

            cc = ET.SubElement(spine_clips[0], "connected-clip", {
                "name": filename,
                "ref": aid,
                "offset": seconds_to_fcpxml(current_offset, common_fr),
                "duration": seconds_to_fcpxml(dur_sec, common_fr),
                "start": seconds_to_fcpxml(in_sec, common_fr),
            })
            print(
                f"  [conn:{track_name}] {count:2d}. {filename[:30]:30s}  "
                f"offset={seconds_to_fcpxml(current_offset, common_fr):>16s}",
                file=sys.stderr,
            )
            current_offset += dur_sec
        elif isinstance(item, GapItem):
            current_offset += max(item.duration_sec, 0.0)


def _build_audio_lane(
    sequence: ET.Element,
    items: list[TrackItem],
    asset_ids: dict[str, str],
    common_fr: FrameRate,
    track_name: str,
) -> None:
    """Build audio track items as <asset-clip> elements in the sequence."""
    _build_track_items(sequence, items, asset_ids, common_fr, f"audio:{track_name}")


def _build_marker(
    parent: ET.Element,
    marker: Marker,
    common_fr: FrameRate,
) -> None:
    """Build a <marker> element on a sequence."""
    ET.SubElement(parent, "marker", {
        "start": seconds_to_fcpxml(marker.time_sec, common_fr),
        "duration": "0s",
        "value": marker.name,
        "color": marker.color.lower(),
    })
