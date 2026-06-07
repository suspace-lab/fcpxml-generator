"""Tests for SRT subtitle generation."""

import json
import os
import tempfile

from fcpxml_generator.subtitles import (
    SubtitleEntry,
    generate_srt,
    generate_srt_file,
    _parse_time,
    _seconds_to_srt_time,
)


class TestParseTime:
    def test_float_seconds(self):
        assert _parse_time(1.5) == 1.5

    def test_srt_timecode(self):
        assert _parse_time("00:00:01,500") == 1.5

    def test_srt_timecode_dot(self):
        assert _parse_time("00:00:01.500") == 1.5

    def test_mm_ss(self):
        assert _parse_time("01:30") == 90.0

    def test_hh_mm_ss(self):
        assert _parse_time("01:00:00") == 3600.0

    def test_int(self):
        assert _parse_time(3) == 3.0


class TestSecondsToSRT:
    def test_zero(self):
        assert _seconds_to_srt_time(0) == "00:00:00,000"

    def test_one_second(self):
        assert _seconds_to_srt_time(1.5) == "00:00:01,500"

    def test_one_minute(self):
        assert _seconds_to_srt_time(90.0) == "00:01:30,000"

    def test_one_hour(self):
        assert _seconds_to_srt_time(3661.123) == "01:01:01,123"


class TestSubtitleEntry:
    def test_to_srt_block(self):
        entry = SubtitleEntry(text="Hello", start_sec=1.0, end_sec=4.0)
        block = entry.to_srt_block(1)
        assert "1\n" in block
        assert "00:00:01,000 --> 00:00:04,000" in block
        assert "Hello" in block

    def test_default_kind(self):
        entry = SubtitleEntry(text="Hi")
        assert entry.kind == "subtitle"


class TestGenerateSRT:
    def test_two_entries(self):
        entries = [
            {"text": "Hello", "start": 0, "end": 2},
            {"text": "World", "start": 2, "end": 5},
        ]
        result = generate_srt(entries)
        assert "1\n" in result
        assert "2\n" in result
        assert "Hello" in result
        assert "World" in result

    def test_empty_entries(self):
        result = generate_srt([])
        assert result == "\n"

    def test_mixed_subtitle_and_title(self):
        entries = [
            {"text": "对话字幕", "start": 0, "end": 3, "type": "subtitle"},
            {"text": "第一章", "start": 3, "end": 6, "type": "title"},
        ]
        result = generate_srt(entries)
        assert "对话字幕" in result
        assert "第一章" in result
        # Both become SRT entries regardless of type
        assert "1\n" in result
        assert "2\n" in result


class TestGenerateSRTFile:
    def test_writes_srt_from_json(self):
        data = [
            {"text": "你好", "start": 0, "end": 2},
            {"text": "世界", "start": 2, "end": 5},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            json_path = os.path.join(tmp, "subtitles.json")
            srt_path = os.path.join(tmp, "subtitles.srt")
            with open(json_path, "w") as f:
                json.dump(data, f)

            result = generate_srt_file(json_path, srt_path)
            assert result == srt_path
            assert os.path.exists(srt_path)
            content = open(srt_path).read()
            assert "你好" in content
            assert "00:00:02,000 --> 00:00:05,000" in content

    def test_auto_output_path(self):
        data = [{"text": "Test", "start": 0, "end": 1}]
        with tempfile.TemporaryDirectory() as tmp:
            json_path = os.path.join(tmp, "captions.json")
            with open(json_path, "w") as f:
                json.dump(data, f)

            result = generate_srt_file(json_path, "")
            assert result.endswith(".srt")

    def test_dict_input_with_subtitles_key(self):
        data = {"subtitles": [{"text": "A", "start": 0, "end": 1}]}
        with tempfile.TemporaryDirectory() as tmp:
            json_path = os.path.join(tmp, "s.json")
            with open(json_path, "w") as f:
                json.dump(data, f)
            result = generate_srt_file(json_path, "")
            assert "A" in open(result).read()

    def test_empty_input_raises(self):
        import pytest
        with tempfile.TemporaryDirectory() as tmp:
            json_path = os.path.join(tmp, "empty.json")
            with open(json_path, "w") as f:
                json.dump([], f)
            with pytest.raises(ValueError):
                generate_srt_file(json_path, "")
