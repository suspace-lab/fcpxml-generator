"""Tests for the FCPXML generator core."""

import json
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from fcpxml_generator.generator import generate_fcpxml, generate_fcpxml_file


# ---------------------------------------------------------------------------
# Minimal valid edit_script for tests (no actual video files needed —
# the generator uses ffprobe, which will fail gracefully with defaults)
# ---------------------------------------------------------------------------

SAMPLE_SCRIPT = {
    "title": "Test Project",
    "clips": [
        {
            "source": "/nonexistent/video1.mp4",
            "filename": "video1.mp4",
            "in": "00:00",
            "out": "00:10",
            "transition": "cut",
        },
        {
            "source": "/nonexistent/video2.mp4",
            "filename": "video2.mp4",
            "in": "00:05",
            "out": "00:15",
            "transition": "dissolve",
        },
    ],
}


# ---------------------------------------------------------------------------
# XML structure tests
# ---------------------------------------------------------------------------

class TestGenerateFCPXML:
    """Test XML document structure without requiring real video files."""

    def test_generates_valid_xml(self):
        xml_str = generate_fcpxml(SAMPLE_SCRIPT)
        # Should parse without error
        root = ET.fromstring(xml_str)
        assert root is not None

    def test_root_is_fcpxml_version_1_9(self):
        xml_str = generate_fcpxml(SAMPLE_SCRIPT)
        root = ET.fromstring(xml_str)
        assert root.tag == "fcpxml"
        assert root.get("version") == "1.9"

    def test_has_resources_section(self):
        xml_str = generate_fcpxml(SAMPLE_SCRIPT)
        root = ET.fromstring(xml_str)
        resources = root.find("resources")
        assert resources is not None

    def test_has_format_definition(self):
        xml_str = generate_fcpxml(SAMPLE_SCRIPT)
        root = ET.fromstring(xml_str)
        fmt = root.find("resources/format")
        assert fmt is not None
        assert fmt.get("id") == "r0"
        assert "frameDuration" in fmt.attrib
        assert "width" in fmt.attrib
        assert "height" in fmt.attrib

    def test_has_asset_for_each_source(self):
        xml_str = generate_fcpxml(SAMPLE_SCRIPT)
        root = ET.fromstring(xml_str)
        assets = root.findall("resources/asset")
        assert len(assets) == 2  # 2 unique sources

    def test_every_asset_has_media_rep_child(self):
        """CRITICAL: FCPXML 1.9 requires <media-rep> inside every <asset>."""
        xml_str = generate_fcpxml(SAMPLE_SCRIPT)
        root = ET.fromstring(xml_str)
        for asset in root.findall("resources/asset"):
            media_reps = asset.findall("media-rep")
            assert len(media_reps) >= 1, (
                f"Asset {asset.get('id')} is missing <media-rep> child"
            )

    def test_has_library_event_project_sequence_spine(self):
        xml_str = generate_fcpxml(SAMPLE_SCRIPT)
        root = ET.fromstring(xml_str)
        library = root.find("library")
        assert library is not None
        event = library.find("event")
        assert event is not None
        project = event.find("project")
        assert project is not None
        sequence = project.find("sequence")
        assert sequence is not None
        spine = sequence.find("spine")
        assert spine is not None

    def test_spine_has_correct_number_of_clips(self):
        xml_str = generate_fcpxml(SAMPLE_SCRIPT)
        root = ET.fromstring(xml_str)
        clips = root.findall("library/event/project/sequence/spine/asset-clip")
        assert len(clips) == 2

    def test_zero_offset_is_0s_not_rational(self):
        """Zero time values must be '0s', not '0/30000s'."""
        xml_str = generate_fcpxml(SAMPLE_SCRIPT)
        root = ET.fromstring(xml_str)
        first_clip = root.find("library/event/project/sequence/spine/asset-clip")
        assert first_clip is not None
        offset = first_clip.get("offset")
        assert offset == "0s", f"Expected '0s' but got '{offset}'"

    def test_clip_has_required_attributes(self):
        xml_str = generate_fcpxml(SAMPLE_SCRIPT)
        root = ET.fromstring(xml_str)
        clip = root.find("library/event/project/sequence/spine/asset-clip")
        assert clip is not None
        for attr in ("name", "ref", "offset", "duration", "start"):
            assert attr in clip.attrib, f"Missing attribute: {attr}"

    def test_empty_clips_raises_value_error(self):
        with pytest.raises(ValueError):
            generate_fcpxml({"title": "Empty", "clips": []})

    def test_override_fps(self):
        xml_str = generate_fcpxml(SAMPLE_SCRIPT, override_fps="24")
        root = ET.fromstring(xml_str)
        fmt = root.find("resources/format")
        assert "24" in fmt.get("frameDuration", "") or "2400" in fmt.get("frameDuration", "")


# ---------------------------------------------------------------------------
# File I/O test
# ---------------------------------------------------------------------------

class TestGenerateFCPXMLFile:
    def test_writes_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(tmpdir, "edit_script.json")
            output_path = os.path.join(tmpdir, "output.fcpxml")

            with open(script_path, "w") as f:
                json.dump(SAMPLE_SCRIPT, f)

            result = generate_fcpxml_file(script_path, output_path)
            assert result == output_path
            assert os.path.exists(output_path)

            # Verify it's valid XML
            tree = ET.parse(output_path)
            assert tree.getroot().tag == "fcpxml"

    def test_auto_output_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(tmpdir, "edit_script.json")

            with open(script_path, "w") as f:
                json.dump(SAMPLE_SCRIPT, f)

            result = generate_fcpxml_file(script_path, "")
            assert result.endswith(".fcpxml")
            assert os.path.exists(result)
            # Title "Test Project" → "Test_Project.fcpxml"
            assert "Test_Project" in result
