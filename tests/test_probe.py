"""Tests for media probing and MediaInfo detection."""

from fcpxml_generator.probe import MediaInfo, probe_media


class TestMediaInfo:
    def test_audio_only_detection(self):
        m = MediaInfo(path="/x/a.mp3", has_video=False, has_audio=True,
                      fps=30.0, duration_sec=120.0, width=0, height=0)
        assert m.is_audio_only
        assert not m.is_video_only

    def test_video_only_detection(self):
        m = MediaInfo(path="/x/v.mp4", has_video=True, has_audio=False,
                      fps=30.0)
        assert m.is_video_only
        assert not m.is_audio_only

    def test_mixed_av(self):
        m = MediaInfo(path="/x/av.mp4", has_video=True, has_audio=True,
                      fps=30.0)
        assert not m.is_audio_only
        assert not m.is_video_only

    def test_slots_defined(self):
        m = MediaInfo(path="/x/test.mp4")
        assert m.has_video is True
        assert m.has_audio is True
        assert m.width == 1920
        assert m.height == 1080


class TestProbeMedia:
    def test_nonexistent_file_returns_defaults(self):
        info = probe_media("/nonexistent/audio.mp3")
        assert info.path.endswith("audio.mp3")
        assert info.duration_sec == 60.0
