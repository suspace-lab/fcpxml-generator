"""
Command-line interface for fcpxml-generator.

Designed for use by both humans and AI agents:
  - Human:  fcpxml edit_script.json -o my_vlog.fcpxml
  - Agent:  fcpxml edit_script.json --fps 29.97 --resolution 1920x1080

The input is always a JSON file (edit_script.json format).
The output is always an FCPXML 1.9 file.
"""

from __future__ import annotations

import argparse
import sys

from .generator import generate_fcpxml_file


def main(argv: list[str] | None = None) -> int:
    """Entry point for the `fcpxml` CLI command.

    Returns 0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        prog="fcpxml",
        description=(
            "Generate FCPXML 1.9 timeline files from an edit script JSON. "
            "Import the output into 剪映专业版 / Final Cut Pro / DaVinci Resolve."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fcpxml edit_script.json
  fcpxml edit_script.json -o my_vlog.fcpxml
  fcpxml edit_script.json --fps 29.97 --resolution 1920x1080
  fcpxml edit_script.json --media-dir ./local_media/

Input format (edit_script.json):
  {
    "title": "My Vlog",
    "clips": [
      {
        "source": "/path/to/video.mp4",
        "in":  "00:00",
        "out": "00:13",
        "transition": "cut"
      }
    ]
  }
        """,
    )

    parser.add_argument(
        "script",
        help="Path to edit_script.json",
    )
    parser.add_argument(
        "-o", "--output",
        default="",
        help="Output .fcpxml file path (default: derived from title)",
    )
    parser.add_argument(
        "--fps",
        default=None,
        help="Override timeline frame rate (e.g. 29.97, 30, 24)",
    )
    parser.add_argument(
        "--resolution",
        default=None,
        help="Override timeline resolution (e.g. 1920x1080, 3840x2160)",
    )
    parser.add_argument(
        "--media-dir",
        default="",
        help="Directory containing local copies of media files "
             "(useful when the edit script was generated on a different machine)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="fcpxml-generator 0.1.0",
    )

    args = parser.parse_args(argv)

    try:
        generate_fcpxml_file(
            args.script,
            output_path=args.output,
            media_dir=args.media_dir,
            override_fps=args.fps,
            override_resolution=args.resolution,
        )
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
