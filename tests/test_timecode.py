"""Tests for timecode utilities."""

import pytest
from fcpxml_generator.timecode import (
    FRAME_RATES,
    FrameRate,
    detect_frame_rate,
    fcpxml_format_name,
    parse_timecode,
    resolve_frame_rate,
    seconds_to_fcpxml,
    seconds_to_frames,
)


class TestDetectFrameRate:
    def test_exact_30(self):
        fr = detect_frame_rate(30.0)
        assert fr == FRAME_RATES["30"]

    def test_exact_29_97(self):
        fr = detect_frame_rate(29.97)
        assert fr == FRAME_RATES["29.97"]

    def test_exact_24(self):
        fr = detect_frame_rate(24.0)
        assert fr == FRAME_RATES["24"]

    def test_exact_25(self):
        fr = detect_frame_rate(25.0)
        assert fr == FRAME_RATES["25"]

    def test_exact_60(self):
        fr = detect_frame_rate(60.0)
        assert fr == FRAME_RATES["60"]

    def test_near_29_97_from_ffprobe(self):
        # ffprobe reports 30000/1001 ≈ 29.97003
        fr = detect_frame_rate(30000 / 1001)
        assert fr == FRAME_RATES["29.97"]

    def test_near_23_976(self):
        fr = detect_frame_rate(24000 / 1001)
        assert fr == FRAME_RATES["23.976"]

    def test_unknown_falls_back_to_30(self):
        fr = detect_frame_rate(48.0)
        assert fr == FRAME_RATES["30"]


class TestResolveFrameRate:
    def test_by_name(self):
        assert resolve_frame_rate("30") == FRAME_RATES["30"]
        assert resolve_frame_rate("29.97") == FRAME_RATES["29.97"]

    def test_by_name_with_fps_suffix(self):
        assert resolve_frame_rate("30fps") == FRAME_RATES["30"]
        assert resolve_frame_rate("29.97fps") == FRAME_RATES["29.97"]

    def test_by_float(self):
        assert resolve_frame_rate("30.0") == FRAME_RATES["30"]

    def test_by_fraction(self):
        assert resolve_frame_rate("30000/1001") == FRAME_RATES["29.97"]

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            resolve_frame_rate("not_a_fps")


class TestSecondsToFCPXML:
    def test_zero_is_always_0s(self):
        fr = FRAME_RATES["30"]
        assert seconds_to_fcpxml(0.0, fr) == "0s"

    def test_one_second_at_30fps(self):
        fr = FRAME_RATES["30"]
        result = seconds_to_fcpxml(1.0, fr)
        assert result == "3000/3000s" or "100/100s"  # 30 frames at 30fps

    def test_one_frame_at_30fps(self):
        fr = FRAME_RATES["30"]
        result = seconds_to_fcpxml(1 / 30, fr)
        assert result == "100/3000s"

    def test_one_frame_at_29_97(self):
        fr = FRAME_RATES["29.97"]
        result = seconds_to_fcpxml(1001 / 30000, fr)
        assert result == "1001/30000s"

    def test_zero_frames_returns_0s(self):
        fr = FRAME_RATES["30"]
        # very small value should round to 0 frames → "0s"
        result = seconds_to_fcpxml(0.0001, fr)
        assert result == "0s"


class TestParseTimecode:
    def test_mm_ss(self):
        assert parse_timecode("01:30") == 90.0

    def test_mm_ss_decimal(self):
        assert parse_timecode("00:13.50") == 13.5

    def test_hh_mm_ss(self):
        assert parse_timecode("01:00:00") == 3600.0

    def test_empty(self):
        assert parse_timecode("") == 0.0


class TestSecondsToFrames:
    def test_at_30fps(self):
        assert seconds_to_frames(1.0, FRAME_RATES["30"]) == 30

    def test_at_24fps(self):
        assert seconds_to_frames(1.0, FRAME_RATES["24"]) == 24


class TestFCPXMLFormatName:
    def test_1080p30(self):
        name = fcpxml_format_name(1920, 1080, FRAME_RATES["30"])
        assert name == "FFVideoFormat1920x1080p30"

    def test_4k_29_97(self):
        name = fcpxml_format_name(3840, 2160, FRAME_RATES["29.97"])
        assert name == "FFVideoFormat3840x2160p29.97"

    def test_720p60(self):
        name = fcpxml_format_name(1280, 720, FRAME_RATES["60"])
        assert name == "FFVideoFormat1280x720p60"
