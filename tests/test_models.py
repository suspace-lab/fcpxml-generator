"""Tests for data models and validation."""

import pytest
from fcpxml_generator.models import (
    ClipItem,
    EditScript,
    GapItem,
    Marker,
    Track,
    ValidationError,
    validate_script,
)


# ---------------------------------------------------------------------------
# EditScript deserialization
# ---------------------------------------------------------------------------

class TestEditScriptFromDict:
    """Parse both old and new JSON formats."""

    def test_new_format_tracks(self):
        data = {
            "title": "Test",
            "tracks": [
                {
                    "name": "V1",
                    "role": "video",
                    "items": [
                        {"type": "clip", "source": "/v/a.mp4", "in": 0, "out": 13},
                        {"type": "gap", "duration": 2},
                        {"type": "clip", "source": "/v/b.mp4", "in": 5, "out": 20},
                    ],
                },
                {
                    "name": "A1",
                    "role": "audio",
                    "items": [
                        {"type": "clip", "source": "/v/music.mp3", "in": 0, "out": 60},
                    ],
                },
            ],
        }
        script = EditScript.from_dict(data)
        assert script.title == "Test"
        assert len(script.tracks) == 2

        v1 = script.tracks[0]
        assert v1.name == "V1"
        assert v1.role == "video"
        assert len(v1.items) == 3
        assert isinstance(v1.items[0], ClipItem)
        assert isinstance(v1.items[1], GapItem)
        assert v1.items[1].duration_sec == 2.0

        a1 = script.tracks[1]
        assert a1.role == "audio"

    def test_old_format_clips(self):
        """Backward compat: flat clips list."""
        data = {
            "title": "Legacy",
            "clips": [
                {"source": "/v/a.mp4", "in": "00:00", "out": "00:13"},
                {"source": "/v/b.mp4", "in": "00:05", "out": "00:20"},
            ],
        }
        script = EditScript.from_dict(data)
        assert script.title == "Legacy"
        assert len(script.tracks) == 1
        assert script.tracks[0].name == "V1"
        assert script.tracks[0].role == "video"
        assert len(script.tracks[0].items) == 2

    def test_parses_timecode_strings(self):
        data = {
            "title": "TC",
            "tracks": [{
                "name": "V1", "role": "video",
                "items": [
                    {"type": "clip", "source": "/v/a.mp4", "in": "01:30", "out": "02:00"},
                ],
            }],
        }
        script = EditScript.from_dict(data)
        clip = script.tracks[0].items[0]
        assert isinstance(clip, ClipItem)
        assert clip.in_sec == 90.0
        assert clip.out_sec == 120.0

    def test_parses_timecode_float_in_old_format(self):
        data = {
            "clips": [
                {"source": "/v/a.mp4", "in": "00:00", "out": "00:13.50"},
            ],
        }
        script = EditScript.from_dict(data)
        clip = script.tracks[0].items[0]
        assert isinstance(clip, ClipItem)
        assert clip.out_sec == 13.5

    def test_with_markers(self):
        data = {
            "title": "With Markers",
            "tracks": [{"name": "V1", "role": "video", "items": []}],
            "markers": [
                {"name": "Chapter 1", "time": 0, "color": "Blue"},
                {"name": "Chapter 2", "time": "01:30", "color": "Red"},
            ],
        }
        script = EditScript.from_dict(data)
        assert len(script.markers) == 2
        assert script.markers[0].time_sec == 0.0
        assert script.markers[1].time_sec == 90.0

    def test_clip_with_filename(self):
        data = {
            "tracks": [{"name": "V1", "role": "video", "items": [
                {"type": "clip", "source": "/v/a.mp4", "filename": "custom_name", "in": 0, "out": 10},
            ]}],
        }
        script = EditScript.from_dict(data)
        clip = script.tracks[0].items[0]
        assert isinstance(clip, ClipItem)
        assert clip.filename == "custom_name"

    def test_all_clip_sources_dedup(self):
        data = {
            "tracks": [
                {"name": "V1", "role": "video", "items": [
                    {"type": "clip", "source": "/v/a.mp4", "in": 0, "out": 5},
                ]},
                {"name": "V2", "role": "video", "items": [
                    {"type": "clip", "source": "/v/a.mp4", "in": 5, "out": 10},
                    {"type": "clip", "source": "/v/b.mp4", "in": 0, "out": 10},
                ]},
            ],
        }
        script = EditScript.from_dict(data)
        sources = script.all_clip_sources
        assert len(sources) == 2
        assert "/v/a.mp4" in sources
        assert "/v/b.mp4" in sources


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------

class TestEditScriptRoundTrip:
    def test_to_dict_and_back(self):
        original = EditScript(
            title="Round Trip",
            fps=29.97,
            resolution="1920x1080",
            tracks=[
                Track(name="V1", role="video", items=[
                    ClipItem(source="/v/a.mp4", in_sec=0, out_sec=13),
                    GapItem(duration_sec=2.0),
                ]),
            ],
            markers=[Marker(name="Start", time_sec=0.0)],
        )
        d = original.to_dict()
        restored = EditScript.from_dict(d)
        assert restored.title == original.title
        assert restored.fps == original.fps
        assert len(restored.tracks) == 1
        assert len(restored.tracks[0].items) == 2
        assert len(restored.markers) == 1


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidateScript:
    def test_valid_script_passes(self):
        script = EditScript(
            title="Valid",
            tracks=[Track(name="V1", role="video", items=[
                ClipItem(source="/v/a.mp4", in_sec=0, out_sec=10),
            ])],
        )
        errors = validate_script(script)
        assert len(errors) == 0

    def test_empty_tracks_fails(self):
        script = EditScript(title="Empty", tracks=[])
        errors = validate_script(script)
        error_paths = [e.path for e in errors]
        assert "tracks" in error_paths

    def test_empty_items_warns(self):
        script = EditScript(
            title="No Items",
            tracks=[Track(name="V1", role="video", items=[])],
        )
        errors = validate_script(script)
        warnings = [e for e in errors if e.severity == "warning"]
        assert len(warnings) >= 1

    def test_inverted_in_out_fails(self):
        script = EditScript(
            title="Inverted",
            tracks=[Track(name="V1", role="video", items=[
                ClipItem(source="/v/a.mp4", in_sec=10, out_sec=5),
            ])],
        )
        errors = validate_script(script)
        assert any("out" in e.message.lower() for e in errors)

    def test_empty_source_fails(self):
        script = EditScript(
            title="No Source",
            tracks=[Track(name="V1", role="video", items=[
                ClipItem(source="", in_sec=0, out_sec=10),
            ])],
        )
        errors = validate_script(script)
        assert any("source" in e.path.lower() for e in errors)

    def test_negative_gap_fails(self):
        script = EditScript(
            title="Bad Gap",
            tracks=[Track(name="V1", role="video", items=[
                ClipItem(source="/v/a.mp4", in_sec=0, out_sec=10),
                GapItem(duration_sec=-1.0),
            ])],
        )
        errors = validate_script(script)
        assert any("gap" in e.message.lower() for e in errors)

    def test_negative_marker_time_warns(self):
        script = EditScript(
            title="Bad Marker",
            tracks=[Track(name="V1", role="video", items=[
                ClipItem(source="/v/a.mp4", in_sec=0, out_sec=10),
            ])],
            markers=[Marker(name="Bad", time_sec=-5.0)],
        )
        errors = validate_script(script)
        assert len(errors) >= 1

    def test_no_clips_at_all_fails(self):
        script = EditScript(
            title="Gaps Only",
            tracks=[Track(name="V1", role="video", items=[
                GapItem(duration_sec=5.0),
            ])],
        )
        errors = validate_script(script)
        assert any("no clips" in e.message.lower() for e in errors)

    def test_multiple_tracks_with_clips(self):
        script = EditScript(
            title="Multi",
            tracks=[
                Track(name="V1", role="video", items=[
                    ClipItem(source="/v/a.mp4", in_sec=0, out_sec=10),
                ]),
                Track(name="A1", role="audio", items=[
                    ClipItem(source="/v/music.mp3", in_sec=0, out_sec=60),
                ]),
            ],
        )
        errors = validate_script(script)
        assert len(errors) == 0
