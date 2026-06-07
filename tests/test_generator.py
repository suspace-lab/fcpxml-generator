"""Tests for the FCPXML generator — multi-track, gaps, markers, compat."""

import json
import os
import tempfile
import xml.etree.ElementTree as ET

import pytest
from fcpxml_generator.generator import generate_fcpxml, generate_fcpxml_file


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

SAMPLE_OLD = {
    "title": "Test Project",
    "clips": [
        {"source": "/n/video1.mp4", "filename": "video1.mp4", "in": "00:00", "out": "00:10"},
        {"source": "/n/video2.mp4", "filename": "video2.mp4", "in": "00:05", "out": "00:15"},
    ],
}

SAMPLE_NEW = {
    "title": "Multi-Track Project",
    "tracks": [
        {
            "name": "V1",
            "role": "video",
            "items": [
                {"type": "clip", "source": "/n/video1.mp4", "in": 0, "out": 10},
                {"type": "gap", "duration": 2},
                {"type": "clip", "source": "/n/video2.mp4", "in": 5, "out": 20},
            ],
        },
        {
            "name": "A1",
            "role": "audio",
            "items": [
                {"type": "clip", "source": "/n/music.mp3", "in": 0, "out": 32},
            ],
        },
    ],
    "markers": [
        {"name": "Chapter 1", "time": 0, "color": "Blue"},
        {"name": "Highlight", "time": 5, "color": "Red"},
    ],
}


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    """Old flat 'clips' format still works."""

    def test_generates_valid_xml(self):
        xml_str = generate_fcpxml(SAMPLE_OLD)
        root = ET.fromstring(xml_str)
        assert root.tag == "fcpxml"

    def test_correct_clip_count(self):
        xml_str = generate_fcpxml(SAMPLE_OLD)
        root = ET.fromstring(xml_str)
        clips = root.findall("library/event/project/sequence/spine/asset-clip")
        assert len(clips) == 2

    def test_zero_offset_is_0s(self):
        xml_str = generate_fcpxml(SAMPLE_OLD)
        root = ET.fromstring(xml_str)
        first = root.find("library/event/project/sequence/spine/asset-clip")
        assert first is not None
        assert first.get("offset") == "0s"


# ---------------------------------------------------------------------------
# Multi-track
# ---------------------------------------------------------------------------

class TestMultiTrack:
    def test_generates_valid_xml(self):
        xml_str = generate_fcpxml(SAMPLE_NEW)
        root = ET.fromstring(xml_str)
        assert root.tag == "fcpxml"

    def test_all_track_clips_present(self):
        xml_str = generate_fcpxml(SAMPLE_NEW, jianying_compat=False)
        root = ET.fromstring(xml_str)
        # V1 clips in spine: 2 (FCPX mode: only primary track on spine)
        spine_clips = root.findall("library/event/project/sequence/spine/asset-clip")
        assert len(spine_clips) == 2
        # A1 clips in sequence (outside spine): 1
        seq_clips = root.findall("library/event/project/sequence/asset-clip")
        assert len(spine_clips) + len(seq_clips) >= 3

    def test_assets_for_all_sources(self):
        xml_str = generate_fcpxml(SAMPLE_NEW)
        root = ET.fromstring(xml_str)
        assets = root.findall("resources/asset")
        # 3 unique sources: video1, video2, music
        assert len(assets) == 3


# ---------------------------------------------------------------------------
# Gaps
# ---------------------------------------------------------------------------

class TestGaps:
    def test_gap_element_present(self):
        xml_str = generate_fcpxml(SAMPLE_NEW)
        root = ET.fromstring(xml_str)
        gaps = root.findall("library/event/project/sequence/spine/gap")
        assert len(gaps) == 1
        assert gaps[0].get("name") == "Gap"

    def test_gap_has_duration(self):
        xml_str = generate_fcpxml(SAMPLE_NEW)
        root = ET.fromstring(xml_str)
        gap = root.find("library/event/project/sequence/spine/gap")
        assert gap is not None
        assert gap.get("duration") is not None
        # 2 seconds at 30fps (default for nonexistent files)
        assert "6000" in gap.get("duration", "") or "0s" != gap.get("duration", "")


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

class TestMarkers:
    def test_markers_present(self):
        xml_str = generate_fcpxml(SAMPLE_NEW)
        root = ET.fromstring(xml_str)
        markers = root.findall("library/event/project/sequence/marker")
        assert len(markers) == 2

    def test_marker_has_value_and_color(self):
        xml_str = generate_fcpxml(SAMPLE_NEW)
        root = ET.fromstring(xml_str)
        m1 = root.findall("library/event/project/sequence/marker")[0]
        assert m1.get("value") == "Chapter 1"
        assert m1.get("color") == "blue"

    def test_first_marker_at_zero(self):
        xml_str = generate_fcpxml(SAMPLE_NEW)
        root = ET.fromstring(xml_str)
        m1 = root.find("library/event/project/sequence/marker")
        assert m1 is not None
        assert m1.get("start") == "0s"


# ---------------------------------------------------------------------------
# FCPXML spec compliance
# ---------------------------------------------------------------------------

class TestFCPXMLCompliance:
    """Critical requirements that caused import failures."""

    def test_every_asset_has_media_rep(self):
        xml_str = generate_fcpxml(SAMPLE_NEW)
        root = ET.fromstring(xml_str)
        for asset in root.findall("resources/asset"):
            media_reps = asset.findall("media-rep")
            assert len(media_reps) >= 1, f"Asset {asset.get('id')} missing <media-rep>"

    def test_zero_offset_is_canonical_0s(self):
        xml_str = generate_fcpxml(SAMPLE_NEW)
        root = ET.fromstring(xml_str)
        first = root.find("library/event/project/sequence/spine/asset-clip")
        assert first is not None
        assert first.get("offset") == "0s"

    def test_root_version_is_1_9(self):
        xml_str = generate_fcpxml(SAMPLE_NEW)
        root = ET.fromstring(xml_str)
        assert root.get("version") == "1.9"

    def test_has_complete_structure(self):
        xml_str = generate_fcpxml(SAMPLE_NEW)
        root = ET.fromstring(xml_str)
        assert root.find("resources/format") is not None
        assert root.find("library/event/project/sequence/spine") is not None

    def test_clip_attributes_complete(self):
        xml_str = generate_fcpxml(SAMPLE_NEW)
        root = ET.fromstring(xml_str)
        clip = root.find("library/event/project/sequence/spine/asset-clip")
        for attr in ("name", "ref", "offset", "duration", "start", "tcFormat"):
            assert attr in clip.attrib, f"Missing: {attr}"

    def test_override_fps(self):
        xml_str = generate_fcpxml(SAMPLE_OLD, override_fps="24")
        root = ET.fromstring(xml_str)
        fmt = root.find("resources/format")
        fd = fmt.get("frameDuration", "")
        assert "24" in fd or "2400" in fd

    def test_override_resolution(self):
        xml_str = generate_fcpxml(SAMPLE_OLD, override_resolution="1280x720")
        root = ET.fromstring(xml_str)
        fmt = root.find("resources/format")
        assert fmt.get("width") == "1280"
        assert fmt.get("height") == "720"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_empty_tracks_raises(self):
        with pytest.raises(ValueError):
            generate_fcpxml({"title": "Empty", "tracks": []})

    def test_no_clips_raises(self):
        with pytest.raises(ValueError):
            generate_fcpxml({"title": "Empty", "tracks": [
                {"name": "V1", "role": "video", "items": [
                    {"type": "gap", "duration": 5},
                ]},
            ]})

    def test_empty_old_clips_raises(self):
        with pytest.raises(ValueError):
            generate_fcpxml({"title": "Empty", "clips": []})


# ---------------------------------------------------------------------------
# Audio-only clips & MediaInfo flags
# ---------------------------------------------------------------------------

AUDIO_ONLY_SCRIPT = {
    "title": "Audio Test",
    "tracks": [
        {"name": "V1", "role": "video", "items": [
            {"type": "clip", "source": "/n/video.mp4", "in": 0, "out": 10},
        ]},
        {"name": "A1", "role": "audio", "items": [
            {"type": "clip", "source": "/n/music.mp3", "in": 0, "out": 30},
        ]},
    ],
}


class TestAudioOnly:
    def test_audio_track_in_sequence(self):
        """Audio clips are placed in <sequence>, not in <spine>."""
        xml_str = generate_fcpxml(AUDIO_ONLY_SCRIPT)
        root = ET.fromstring(xml_str)
        seq = root.find("library/event/project/sequence")
        # Audio clips directly in sequence, outside spine
        audio_clips = seq.findall("asset-clip")
        assert len(audio_clips) >= 1

    def test_spine_only_has_video(self):
        xml_str = generate_fcpxml(AUDIO_ONLY_SCRIPT)
        root = ET.fromstring(xml_str)
        spine_clips = root.findall("library/event/project/sequence/spine/asset-clip")
        # Only the video track clip is in the spine
        assert len(spine_clips) == 1


# ---------------------------------------------------------------------------
# Connected clips (secondary video tracks)
# ---------------------------------------------------------------------------

CONNECTED_SCRIPT = {
    "title": "B-Roll Test",
    "tracks": [
        {"name": "V1", "role": "video", "items": [
            {"type": "clip", "source": "/n/main.mp4", "in": 0, "out": 10},
        ]},
        {"name": "V2", "role": "video", "items": [
            {"type": "clip", "source": "/n/broll.mp4", "in": 0, "out": 5},
        ]},
    ],
}


class TestConnectedClips:
    def test_connected_clip_present(self):
        """FCPX/Resolve mode: secondary tracks → connected-clip."""
        xml_str = generate_fcpxml(CONNECTED_SCRIPT, jianying_compat=False)
        root = ET.fromstring(xml_str)
        ccs = root.findall("library/event/project/sequence/spine/asset-clip/connected-clip")
        assert len(ccs) >= 1

    def test_spine_has_one_clip_in_fcpx_mode(self):
        xml_str = generate_fcpxml(CONNECTED_SCRIPT, jianying_compat=False)
        root = ET.fromstring(xml_str)
        spine_clips = root.findall("library/event/project/sequence/spine/asset-clip")
        assert len(spine_clips) == 1  # Primary only; secondary = connected-clip children

    def test_jianying_mode_flattens_all_tracks(self):
        """剪映 compat: all video tracks flattened to spine."""
        xml_str = generate_fcpxml(CONNECTED_SCRIPT, jianying_compat=True)
        root = ET.fromstring(xml_str)
        spine_clips = root.findall("library/event/project/sequence/spine/asset-clip")
        assert len(spine_clips) == 2  # V1 + V2 both flat on spine

    def test_jianying_mode_no_connected_clips(self):
        """剪映 compat: zero <connected-clip> elements."""
        xml_str = generate_fcpxml(CONNECTED_SCRIPT, jianying_compat=True)
        root = ET.fromstring(xml_str)
        ccs = root.findall(".//connected-clip")
        assert len(ccs) == 0


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------

class TestDryRun:
    def test_dry_run_does_not_write_file(self):
        import tempfile, json as _json
        with tempfile.TemporaryDirectory() as tmp:
            script_path = os.path.join(tmp, "edit_script.json")
            out_path = os.path.join(tmp, "out.fcpxml")
            with open(script_path, "w") as f:
                _json.dump(SAMPLE_OLD, f)

            result = generate_fcpxml_file(script_path, out_path, dry_run=True)
            # Should return the output path but not write the file
            assert not os.path.exists(out_path) or os.path.getsize(out_path) == 0

# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

class TestFileIO:
    def test_writes_file_from_new_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = os.path.join(tmp, "edit_script.json")
            out_path = os.path.join(tmp, "out.fcpxml")
            with open(script_path, "w") as f:
                json.dump(SAMPLE_NEW, f)
            result = generate_fcpxml_file(script_path, out_path)
            assert result == out_path
            assert os.path.exists(out_path)
            tree = ET.parse(out_path)
            assert tree.getroot().tag == "fcpxml"

    def test_auto_output_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            script_path = os.path.join(tmp, "edit_script.json")
            with open(script_path, "w") as f:
                json.dump(SAMPLE_NEW, f)
            result = generate_fcpxml_file(script_path, "")
            assert result.endswith(".fcpxml")
            assert "Multi_Track_Project" in result
