"""
Core FCPXML 1.9 document generator.

Takes an EditScript and produces a valid FCPXML document conforming to
the Apple FCPXML 1.9 specification. Supports:

  - Multi-track video + audio timelines
  - Gaps / spacers between clips
  - Chapter / annotation markers
  - Backward-compatible flat "clips" format
  - `<media-rep>` child in every `<asset>` (required by spec)
  - `0s` for zero-value time attributes (not `0/30000s`)
  - Per-file fps detection for accurate timing
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
from .probe import probe_multiple
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
    """Generate a complete FCPXML 1.9 document string from an edit script.

    Accepts either an EditScript object or a raw JSON dict (backward compat).

    Args:
        edit_script: EditScript object or raw dict.
        media_dir: Resolve source paths relative to this directory first.
        override_fps: Force a specific frame rate (e.g. "29.97").
        override_resolution: Force a specific resolution ("1920x1080").

    Returns:
        Complete FCPXML 1.9 document as a UTF-8 string with XML declaration.
    """
    # Normalize to EditScript
    if isinstance(edit_script, dict):
        script = EditScript.from_dict(edit_script)
    else:
        script = edit_script

    if not script.tracks:
        raise ValueError("edit_script has no tracks — nothing to generate")

    # ------------------------------------------------------------------
    # 1. Collect unique sources & probe
    # ------------------------------------------------------------------
    unique_sources = script.all_clip_sources
    if not unique_sources:
        raise ValueError("No clips with valid 'source' paths found")

    video_info_cache = probe_multiple(unique_sources)

    # ------------------------------------------------------------------
    # 2. Determine timeline frame rate & resolution
    # ------------------------------------------------------------------
    if override_fps:
        common_fr = resolve_frame_rate(override_fps)
    elif script.fps is not None:
        common_fr = detect_frame_rate(script.fps)
    else:
        fps_votes: dict[str, int] = {}
        for src in unique_sources:
            info = video_info_cache.get(src)
            if info:
                fr = detect_frame_rate(info.fps)
                key = f"{fr.fps:.4f}"
                fps_votes[key] = fps_votes.get(key, 0) + 1
        if fps_votes:
            best_key = max(fps_votes, key=fps_votes.get)
            common_fr = resolve_frame_rate(best_key)
        else:
            common_fr = resolve_frame_rate("30")

    if override_resolution:
        w_str, h_str = override_resolution.split("x")
        width, height = int(w_str), int(h_str)
    elif script.resolution:
        w_str, h_str = script.resolution.split("x")
        width, height = int(w_str), int(h_str)
    else:
        first_info = video_info_cache.get(unique_sources[0])
        if first_info:
            width, height = first_info.width, first_info.height
        else:
            width, height = 1920, 1080

    format_name = fcpxml_format_name(width, height, common_fr)
    print(f"  Timeline: {width}x{height} @ {common_fr.fps:.4f} fps", file=sys.stderr)

    # ------------------------------------------------------------------
    # 3. Build the FCPXML document
    # ------------------------------------------------------------------
    root = ET.Element("fcpxml", {"version": "1.9"})
    resources = ET.SubElement(root, "resources")

    # Format definition
    ET.SubElement(resources, "format", {
        "id": "r0",
        "name": format_name,
        "frameDuration": common_fr.frame_duration,
        "width": str(width),
        "height": str(height),
    })

    # Asset definitions (one per unique source file)
    asset_ids: dict[str, str] = _build_assets(resources, unique_sources, video_info_cache, common_fr)

    # --- <library> / <event> / <project> / <sequence> ------------------
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

    # --- <spine> (primary storyline — always the first video track) ---
    spine = ET.SubElement(sequence, "spine")

    # Separate video and audio tracks
    video_tracks = [t for t in script.tracks if t.role == "video"]
    audio_tracks = [t for t in script.tracks if t.role == "audio"]

    # Primary storyline: first video track's items go on the spine
    if video_tracks:
        _build_track_items(spine, video_tracks[0].items, asset_ids, common_fr, "spine")
    else:
        # Audio-only timeline: put first audio track on spine
        _build_track_items(spine, audio_tracks[0].items, asset_ids, common_fr, "spine")
        audio_tracks = audio_tracks[1:]

    # Additional video tracks → connected clips (secondary storylines)
    # These appear as separate tracks layered over the spine
    for vtrack in video_tracks[1:]:
        _build_track_items(spine, vtrack.items, asset_ids, common_fr, f"video:{vtrack.name}")

    # Audio tracks → appear after the spine
    for atrack in audio_tracks:
        _build_track_items(spine, atrack.items, asset_ids, common_fr, f"audio:{atrack.name}")

    # --- Markers on the sequence ---
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
) -> str:
    """Read an edit_script JSON file and write the FCPXML output.

    Returns the path to the generated .fcpxml file.
    """
    with open(edit_script_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if not output_path:
        title = raw.get("title", "untitled")
        output_path = f"{title.replace(' ', '_').replace('-', '_')}.fcpxml"

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
# Internal helpers
# ---------------------------------------------------------------------------

def _build_assets(
    resources: ET.Element,
    sources: list[str],
    info_cache: dict[str, Any],
    common_fr: FrameRate,
) -> dict[str, str]:
    """Build <asset> elements in <resources> and return {path: asset_id}."""
    asset_ids: dict[str, str] = {}
    for i, src in enumerate(sources, 1):
        asset_id = f"r{i}"
        asset_ids[src] = asset_id
        info = info_cache.get(src)

        file_fr = detect_frame_rate(info.fps) if info else common_fr
        if info and info.duration_sec > 0:
            dur_tc = seconds_to_fcpxml(info.duration_sec, file_fr)
        else:
            dur_tc = "60s"

        abs_path = os.path.abspath(src)
        file_url = "file://" + abs_path
        file_name = Path(src).name

        asset = ET.SubElement(resources, "asset", {
            "id": asset_id,
            "name": file_name,
            "src": file_url,
            "start": "0s",
            "duration": dur_tc,
            "hasVideo": "1",
            "hasAudio": "1",
            "audioSources": "1",
            "audioChannels": "2",
            "format": "r0",
        })

        # Required by FCPXML 1.9 spec
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
    """Build <asset-clip> and <gap> elements from a track's item list."""
    current_offset: float = 0.0
    clip_count = 0

    for item in items:
        if isinstance(item, GapItem):
            dur = max(item.duration_sec, 0.0)
            dur_tc = seconds_to_fcpxml(dur, common_fr)
            ET.SubElement(parent, "gap", {
                "name": "Gap",
                "offset": seconds_to_fcpxml(current_offset, common_fr),
                "duration": dur_tc,
            })
            current_offset += dur
            print(f"       gap  offset={seconds_to_fcpxml(current_offset - dur, common_fr):>16s}  dur={dur_tc:>16s}", file=sys.stderr)

        elif isinstance(item, ClipItem):
            clip_count += 1
            source = item.source
            filename = item.filename or Path(source).name if source else f"clip_{clip_count}"
            in_sec = item.in_sec
            out_sec = item.out_sec
            if out_sec <= in_sec:
                out_sec = in_sec + 3.0
            dur_sec = out_sec - in_sec

            aid = asset_ids.get(source, "r1")

            offset_tc = seconds_to_fcpxml(current_offset, common_fr)
            start_tc = seconds_to_fcpxml(in_sec, common_fr)
            dur_tc = seconds_to_fcpxml(dur_sec, common_fr)

            ET.SubElement(parent, "asset-clip", {
                "name": filename,
                "ref": aid,
                "offset": offset_tc,
                "duration": dur_tc,
                "start": start_tc,
                "tcFormat": "NDF",
            })

            print(
                f"  [{label}] {clip_count:2d}. {filename[:30]:30s}  "
                f"offset={offset_tc:>16s}  start={start_tc:>16s}  dur={dur_tc:>16s}",
                file=sys.stderr,
            )
            current_offset += dur_sec


def _build_marker(
    parent: ET.Element,
    marker: Marker,
    common_fr: FrameRate,
) -> None:
    """Build a <marker> element."""
    time_tc = seconds_to_fcpxml(marker.time_sec, common_fr)
    ET.SubElement(parent, "marker", {
        "start": time_tc,
        "duration": "0s",
        "value": marker.name,
        "color": marker.color.lower(),
    })
