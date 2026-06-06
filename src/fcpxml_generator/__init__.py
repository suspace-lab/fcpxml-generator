"""
FCPXML Generator — produce Final Cut Pro X XML (FCPXML 1.9) timeline files.

CLI:
    fcpxml generate edit_script.json -o timeline.fcpxml
    fcpxml probe video.mp4 --format json
    fcpxml validate edit_script.json

Programmatic:
    from fcpxml_generator import generate_fcpxml, EditScript, validate_script

    xml = generate_fcpxml(edit_script_dict)
    script = EditScript.from_dict(data)
    errors = validate_script(script)
"""

from .generator import generate_fcpxml, generate_fcpxml_file
from .models import (
    ClipItem,
    EditScript,
    GapItem,
    Marker,
    Track,
    ValidationError,
    validate_script,
)
from .probe import MediaInfo, probe_media, probe_multiple, probe_video
from .timecode import (
    detect_frame_rate,
    parse_timecode,
    resolve_frame_rate,
    seconds_to_fcpxml,
)

__version__ = "0.1.0"

__all__ = [
    # Generator
    "generate_fcpxml",
    "generate_fcpxml_file",
    # Models
    "EditScript",
    "Track",
    "ClipItem",
    "GapItem",
    "Marker",
    "ValidationError",
    "validate_script",
    # Probe
    "MediaInfo",
    "probe_media",
    "probe_video",
    "probe_multiple",
    # Timecode
    "detect_frame_rate",
    "resolve_frame_rate",
    "parse_timecode",
    "seconds_to_fcpxml",
]
