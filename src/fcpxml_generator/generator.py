"""
Core FCPXML 1.9 document generator.

Takes an edit script (JSON dict) and produces a valid FCPXML document
conforming to the Apple FCPXML 1.9 specification.

Key features:
  - `<media-rep>` child in every `<asset>` element (required by spec)
  - `0s` for zero-value time attributes (not `0/30000s`)
  - Per-file fps detection for accurate timing
  - Clean XML output with proper indentation
"""

from __future__ import annotations

import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .probe import VideoInfo, probe_multiple
from .timecode import (
    FrameRate,
    detect_frame_rate,
    fcpxml_format_name,
    parse_timecode,
    resolve_frame_rate,
    seconds_to_fcpxml,
    seconds_to_frames,
)


# ---------------------------------------------------------------------------
# Input schema (edit_script.json format)
# ---------------------------------------------------------------------------
# {
#   "title": "My Vlog",
#   "fps": 30.0,                    # optional; auto-detected if omitted
#   "resolution": "1920x1080",      # optional; from first video if omitted
#   "clips": [
#     {
#       "source": "/path/to/video.mp4",
#       "filename": "video.mp4",             # optional; derived from source
#       "in": "00:00",                        # MM:SS or HH:MM:SS
#       "out": "00:13",                       # in/out → source_range
#       "duration": "0:13",                   # informational only
#       "description": "...",                 # optional; for reference
#       "transition": "cut"                   # optional; informational only
#     }
#   ]
# }


def generate_fcpxml(
    edit_script: dict[str, Any],
    *,
    media_dir: str = "",
    override_fps: str | None = None,
    override_resolution: str | None = None,
) -> str:
    """Generate a complete FCPXML 1.9 document string from an edit script.

    Args:
        edit_script: Parsed edit script dict (see schema above).
        media_dir: If provided, resolve source paths relative to this
                   directory first (useful when the edit script was
                   generated on a different machine).
        override_fps: Force a specific frame rate (e.g. "29.97").
        override_resolution: Force a specific resolution (e.g. "1920x1080").

    Returns:
        A complete FCPXML 1.9 document as a string (UTF-8, with XML decl).
    """
    title = edit_script.get("title", "Untitled Project")
    clips_data: list[dict[str, Any]] = edit_script.get("clips", [])

    if not clips_data:
        raise ValueError("edit_script has no clips — nothing to generate")

    # ------------------------------------------------------------------
    # 1. Collect unique sources & probe
    # ------------------------------------------------------------------
    unique_sources: list[str] = list(dict.fromkeys(
        c.get("source", "") for c in clips_data if c.get("source")
    ))
    if not unique_sources:
        raise ValueError("No clips with valid 'source' paths found")

    video_info_cache = probe_multiple(unique_sources)

    # ------------------------------------------------------------------
    # 2. Determine timeline frame rate & resolution
    # ------------------------------------------------------------------
    if override_fps:
        common_fr = resolve_frame_rate(override_fps)
    else:
        # Use the most common fps among all clips
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

    # --- <resources> ---------------------------------------------------
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
    asset_ids: dict[str, str] = {}
    for i, src in enumerate(unique_sources, 1):
        asset_id = f"r{i}"
        asset_ids[src] = asset_id
        info = video_info_cache.get(src)

        # Use per-file fps for accurate asset duration
        file_fr = detect_frame_rate(info.fps) if info else common_fr

        if info and info.duration_sec > 0:
            duration_tc = seconds_to_fcpxml(info.duration_sec, file_fr)
        else:
            duration_tc = "60s"

        abs_path = os.path.abspath(src)
        file_url = "file://" + abs_path
        file_name = Path(src).name

        asset = ET.SubElement(resources, "asset", {
            "id": asset_id,
            "name": file_name,
            "src": file_url,
            "start": "0s",
            "duration": duration_tc,
            "hasVideo": "1",
            "hasAudio": "1",
            "audioSources": "1",
            "audioChannels": "2",
            "format": "r0",
        })

        # --- CRITICAL: <media-rep> child element (required by FCPXML 1.9) ---
        ET.SubElement(asset, "media-rep", {
            "kind": "original-media",
            "src": file_url,
        })

    # --- <library> / <event> / <project> / <sequence> ------------------
    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event", {"name": title})
    project = ET.SubElement(event, "project", {"name": title})
    sequence = ET.SubElement(project, "sequence", {
        "format": "r0",
        "duration": "0s",  # placeholder; many importers ignore this
        "tcStart": "0s",
        "tcFormat": "NDF",
        "audioLayout": "stereo",
        "audioRate": "48k",
    })

    # --- <spine> (primary storyline) -----------------------------------
    spine = ET.SubElement(sequence, "spine")

    # Build clips
    current_offset_seconds: float = 0.0

    for i, clip in enumerate(clips_data, 1):
        source = clip.get("source", "")
        filename = clip.get("filename", Path(source).name if source else f"clip_{i}")
        in_sec = parse_timecode(clip.get("in", "00:00"))
        out_sec = parse_timecode(clip.get("out", "00:00"))
        if out_sec <= in_sec:
            out_sec = in_sec + 3.0  # minimum 3-second clip
        duration_sec = out_sec - in_sec

        asset_id = asset_ids.get(source, "r1")

        # Timing values in FCPXML rational format
        offset_tc = seconds_to_fcpxml(current_offset_seconds, common_fr)
        start_tc = seconds_to_fcpxml(in_sec, common_fr)
        duration_tc = seconds_to_fcpxml(duration_sec, common_fr)

        ET.SubElement(spine, "asset-clip", {
            "name": filename,
            "ref": asset_id,
            "offset": offset_tc,
            "duration": duration_tc,
            "start": start_tc,
            "tcFormat": "NDF",
        })

        print(
            f"  [{i:2d}] {filename[:30]:30s}  "
            f"offset={offset_tc:>16s}  start={start_tc:>16s}  dur={duration_tc:>16s}",
            file=sys.stderr,
        )

        current_offset_seconds += duration_sec

    # ------------------------------------------------------------------
    # 4. Serialize to string
    # ------------------------------------------------------------------

    # Pretty-print with indentation (Python 3.9+ built-in)
    ET.indent(root, space="  ")

    # Build output string
    import io
    buf = io.BytesIO()
    buf.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    tree = ET.ElementTree(root)
    tree.write(buf, encoding="utf-8", xml_declaration=False)
    result = buf.getvalue().decode("utf-8") + "\n"

    return result


def generate_fcpxml_file(
    edit_script_path: str,
    output_path: str = "",
    *,
    media_dir: str = "",
    override_fps: str | None = None,
    override_resolution: str | None = None,
) -> str:
    """Read an edit_script JSON file and write the FCPXML output file.

    Args:
        edit_script_path: Path to edit_script.json.
        output_path: Path for the output .fcpxml file. Auto-derived if empty.
        media_dir: Directory to look for media files (overrides paths in script).
        override_fps: Force timeline frame rate.
        override_resolution: Force timeline resolution.

    Returns:
        Path to the generated .fcpxml file.
    """
    with open(edit_script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    if not output_path:
        title = script.get("title", "untitled")
        safe_title = title.replace(" ", "_").replace("-", "_")
        output_path = f"{safe_title}.fcpxml"

    xml_string = generate_fcpxml(
        script,
        media_dir=media_dir,
        override_fps=override_fps,
        override_resolution=override_resolution,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_string)

    print(f"\n✅ FCPXML generated: {output_path}", file=sys.stderr)
    print(f"   Import: 剪映专业版 → 导入工程 → 选择此文件", file=sys.stderr)
    return output_path

