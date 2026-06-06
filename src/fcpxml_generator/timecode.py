"""
Timecode and frame-rate utilities for FCPXML generation.

FCPXML uses rational time values (e.g. "1001/30000s" for 29.97 fps).
This module handles all time conversion and frame-rate normalisation.

FCPXML 1.9 time encoding rules:
  - 29.97 fps → frameDuration = 1001/30000s, N frames = N*1001/30000s
  - 30 fps    → frameDuration = 100/3000s,   N frames = N*100/3000s
  - 25 fps    → frameDuration = 100/2500s,   N frames = N*100/2500s
  - 23.976 fps→ frameDuration = 1001/24000s, N frames = N*1001/24000s
  - 24 fps    → frameDuration = 100/2400s,   N frames = N*100/2400s
  - 59.94 fps → frameDuration = 1001/60000s, N frames = N*1001/60000s
  - 60 fps    → frameDuration = 100/6000s,   N frames = N*100/6000s

For zero values (0 frames / 0 seconds), ALWAYS use "0s" not "0/xxx s".
"""

from fractions import Fraction
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Frame rate definitions
# ---------------------------------------------------------------------------

class FrameRate(NamedTuple):
    """Normalised frame rate with FCPXML representation."""
    fps: float               # Approximate float value (e.g. 29.97)
    exact: Fraction          # Exact rational value (e.g. 30000/1001)
    frame_duration: str      # FCPXML frameDuration string
    frame_multiplier: tuple[int, int]  # (numerator, denominator) → N * num/denom

    @property
    def numerator(self) -> int:
        return self.frame_multiplier[0]

    @property
    def denominator(self) -> int:
        return self.frame_multiplier[1]


# All standard frame rates supported by FCPXML 1.9
FRAME_RATES: dict[str, FrameRate] = {
    "23.976": FrameRate(
        fps=23.976,
        exact=Fraction(24000, 1001),
        frame_duration="1001/24000s",
        frame_multiplier=(1001, 24000),
    ),
    "24": FrameRate(
        fps=24.0,
        exact=Fraction(24, 1),
        frame_duration="100/2400s",
        frame_multiplier=(100, 2400),
    ),
    "25": FrameRate(
        fps=25.0,
        exact=Fraction(25, 1),
        frame_duration="100/2500s",
        frame_multiplier=(100, 2500),
    ),
    "29.97": FrameRate(
        fps=29.97,
        exact=Fraction(30000, 1001),
        frame_duration="1001/30000s",
        frame_multiplier=(1001, 30000),
    ),
    "30": FrameRate(
        fps=30.0,
        exact=Fraction(30, 1),
        frame_duration="100/3000s",
        frame_multiplier=(100, 3000),
    ),
    "59.94": FrameRate(
        fps=59.94,
        exact=Fraction(60000, 1001),
        frame_duration="1001/60000s",
        frame_multiplier=(1001, 60000),
    ),
    "60": FrameRate(
        fps=60.0,
        exact=Fraction(60, 1),
        frame_duration="100/6000s",
        frame_multiplier=(100, 6000),
    ),
}


def detect_frame_rate(fps: float) -> FrameRate:
    """Match a float fps value to the nearest standard FrameRate.

    Args:
        fps: Approximate frames per second (e.g. 29.97, 30.0)

    Returns:
        The closest standard FrameRate. Falls back to 30fps if no match.
    """
    best: FrameRate | None = None
    best_diff = float("inf")

    for fr in FRAME_RATES.values():
        diff = abs(fps - fr.fps)
        if diff < best_diff:
            best_diff = diff
            best = fr
        # exact match shortcut
        if diff < 0.001:
            break

    # If the closest match is too far (> 3 fps), fall back to 30
    if best is None or best_diff > 3.0:
        return FRAME_RATES["30"]

    return best


def resolve_frame_rate(name_or_fps: str) -> FrameRate:
    """Resolve a frame rate from a string name or numeric value.

    Accepts:
        "30", "29.97", "24", "25", "23.976", "60", "59.94"
        "30000/1001", "24000/1001"
        "30fps", "29.97fps"

    Args:
        name_or_fps: Frame rate identifier string.

    Returns:
        Resolved FrameRate.

    Raises:
        ValueError: If the string cannot be parsed.
    """
    s = name_or_fps.strip().lower().removesuffix("fps")

    # Try direct key lookup
    if s in FRAME_RATES:
        return FRAME_RATES[s]

    # Try exact fraction (e.g. "30000/1001")
    if "/" in s:
        try:
            num, den = s.split("/")
            frac = Fraction(int(num), int(den))
            for fr in FRAME_RATES.values():
                if fr.exact == frac:
                    return fr
        except (ValueError, ZeroDivisionError):
            pass

    # Try float match
    try:
        f = float(s)
        return detect_frame_rate(f)
    except ValueError:
        pass

    raise ValueError(
        f"Unknown frame rate '{name_or_fps}'. "
        f"Supported: {', '.join(FRAME_RATES.keys())}"
    )


# ---------------------------------------------------------------------------
# Time → FCPXML rational-string conversion
# ---------------------------------------------------------------------------

def seconds_to_fcpxml(seconds: float, fr: FrameRate) -> str:
    """Convert a time in seconds to an FCPXML rational time string.

    For zero seconds, always returns "0s" (not "0/30000s" etc.),
    as required by the FCPXML 1.9 specification.

    Args:
        seconds: Time value in seconds.
        fr: Target FrameRate.

    Returns:
        FCPXML time string, e.g. "1001/30000s" or "0s".
    """
    # Zero → always "0s"
    if seconds == 0.0:
        return "0s"

    frames = int(round(seconds * fr.exact))
    if frames == 0:
        return "0s"

    num = frames * fr.numerator
    den = fr.denominator
    return f"{num}/{den}s"


def seconds_to_frames(seconds: float, fr: FrameRate) -> int:
    """Convert seconds to frame count at the given frame rate."""
    return int(round(seconds * fr.exact))


# ---------------------------------------------------------------------------
# Human-readable timecode parsing (MM:SS.mmm / HH:MM:SS.mmm)
# ---------------------------------------------------------------------------

def parse_timecode(tc: str) -> float:
    """Parse a human-readable timecode to seconds.

    Formats accepted:
      "MM:SS.mmm"   → minutes:seconds
      "HH:MM:SS.mmm" → hours:minutes:seconds
      "MM:SS"       → minutes:seconds (integers)
      "HH:MM:SS"    → hours:minutes:seconds (integers)

    Args:
        tc: Timecode string.

    Returns:
        Time in seconds.
    """
    tc = tc.strip()
    parts = tc.split(":")
    if len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    elif len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    return 0.0


def format_timecode(seconds: float) -> str:
    """Format seconds as MM:SS.mm (2 decimal places)."""
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02d}:{s:05.2f}"


# ---------------------------------------------------------------------------
# FCPXML format name
# ---------------------------------------------------------------------------

def fcpxml_format_name(width: int, height: int, fr: FrameRate) -> str:
    """Return the standard FCPXML format name for a resolution + frame rate.

    Args:
        width: Video width in pixels.
        height: Video height in pixels.
        fr: Target FrameRate.

    Returns:
        Standard format name, e.g. "FFVideoFormat1920x1080p30".
    """
    # Standard FCP format basenames
    resolution_map = {
        (3840, 2160): "FFVideoFormat3840x2160",
        (1920, 1080): "FFVideoFormat1920x1080",
        (1280, 720):  "FFVideoFormat1280x720",
    }

    base = resolution_map.get((width, height), f"FFVideoFormat{width}x{height}")

    # FPS suffix
    fps_suffix_map = {
        "23.976": "p23.98",
        "24":     "p24",
        "25":     "p25",
        "29.97":  "p29.97",
        "30":     "p30",
        "59.94":  "p59.94",
        "60":     "p60",
    }

    # Find the key for this FrameRate
    for key, fr_val in FRAME_RATES.items():
        if fr_val == fr:
            suffix = fps_suffix_map.get(key, f"p{int(fr.fps)}")
            return f"{base}{suffix}"

    return f"{base}p{int(fr.fps)}"
