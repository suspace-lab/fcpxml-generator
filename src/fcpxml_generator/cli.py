"""
Command-line interface for fcpxml-generator.

Subcommands:
  fcpxml generate <script> [-o output] [--fps 30] [--resolution 1920x1080]
  fcpxml probe <video...>  [--format json|text]
  fcpxml validate <script> [--json]

For backward compatibility, bare invocation is treated as 'generate':
  fcpxml <script> [-o output] [--fps 30]

Designed for both humans and AI agents. All subcommands return
structured JSON when --format json is used.
"""

from __future__ import annotations

import argparse
import json
import sys

from .generator import generate_fcpxml_file
from .models import EditScript, validate_script
from .probe import probe_video


def main(argv: list[str] | None = None) -> int:
    """Entry point for `fcpxml` CLI. Returns 0 on success, 1 on error."""
    parser = _build_parser()

    # Detect bare invocation (no subcommand)
    if argv is None:
        argv = sys.argv[1:]
    cmd, args = _detect_command(argv)

    if cmd == "generate":
        return _cmd_generate(args)
    elif cmd == "probe":
        return _cmd_probe(args)
    elif cmd == "validate":
        return _cmd_validate(args)
    elif cmd == "help":
        parser.print_help()
        return 0
    else:
        parser.print_help()
        return 1


# ---------------------------------------------------------------------------
# Parser setup
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    """Build the full argument parser."""
    parser = argparse.ArgumentParser(
        prog="fcpxml",
        description="FCPXML Generator — produce FCPXML 1.9 timeline files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fcpxml edit_script.json                     # generate (bare)
  fcpxml generate edit_script.json -o vlog.fcpxml
  fcpxml generate edit_script.json --fps 29.97 --resolution 1920x1080
  fcpxml probe video.mp4 --format json
  fcpxml validate edit_script.json --json
        """,
    )
    parser.add_argument(
        "--version", action="version", version="fcpxml-generator 0.1.0",
    )
    subs = parser.add_subparsers(dest="command", title="subcommands")

    # generate
    g = subs.add_parser("generate", help="Generate FCPXML from an edit script")
    g.add_argument("script", help="Path to edit_script.json")
    g.add_argument("-o", "--output", default="", help="Output .fcpxml file")
    g.add_argument("--fps", default=None, help="Override frame rate (e.g. 29.97)")
    g.add_argument("--resolution", default=None, help="Override resolution (WxH)")
    g.add_argument("--media-dir", default="", help="Local media directory")
    g.add_argument("--dry-run", action="store_true",
                   help="Preview timeline without writing FCPXML")
    g.add_argument("--jianying", action="store_true",
                   help="剪映兼容模式：扁平化所有轨道到 spine（不用 connected-clip）")
    g.set_defaults(_subcmd="generate")

    # probe
    p = subs.add_parser("probe", help="Probe video files → JSON/text metadata")
    p.add_argument("videos", nargs="+", help="Video file path(s)")
    p.add_argument("--format", choices=["text", "json"], default="text",
                   help="Output format")
    p.set_defaults(_subcmd="probe")

    # validate
    v = subs.add_parser("validate", help="Validate an edit script")
    v.add_argument("script", help="Path to edit_script.json")
    v.add_argument("--json", action="store_true", help="Output as JSON")
    v.set_defaults(_subcmd="validate")

    return parser


def _detect_command(argv: list[str]) -> tuple[str, argparse.Namespace]:
    """Detect which subcommand the user wants.

    Handles bare invocation: `fcpxml script.json` → generate.
    """
    if not argv:
        return ("help", argparse.Namespace())

    if argv[0] in ("-h", "--help"):
        return ("help", argparse.Namespace())

    if argv[0] in ("generate", "probe", "validate"):
        parser = _build_parser()
        args = parser.parse_args(argv)
        return (argv[0], args)

    # Bare invocation → treat as 'generate'
    return _parse_bare_generate(argv)


def _parse_bare_generate(argv: list[str]) -> tuple[str, argparse.Namespace]:
    """Parse bare `fcpxml script.json [options]` as generate."""
    parser = argparse.ArgumentParser(
        prog="fcpxml",
        description="Generate FCPXML from an edit script (bare invocation).",
        add_help=False,
    )
    parser.add_argument("script", help="Path to edit_script.json")
    parser.add_argument("-o", "--output", default="", help="Output .fcpxml file")
    parser.add_argument("--fps", default=None, help="Override frame rate")
    parser.add_argument("--resolution", default=None, help="Override resolution")
    parser.add_argument("--media-dir", default="", help="Local media directory")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview timeline without writing FCPXML")
    parser.add_argument("--jianying", action="store_true",
                       help="剪映兼容模式")
    parser.add_argument("--version", action="version", version="fcpxml-generator 0.1.0")

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # If bare parsing fails, try full parser for help
        full_parser = _build_parser()
        full_parser.parse_args(argv)
        return ("help", argparse.Namespace())

    return ("generate", args)


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def _cmd_generate(args: argparse.Namespace) -> int:
    """`fcpxml generate` — core FCPXML generation."""
    try:
        dry_run = getattr(args, "dry_run", False)
        jianying = getattr(args, "jianying", False) or getattr(args, "jianying_compat", False)
        generate_fcpxml_file(
            args.script,
            output_path=args.output,
            media_dir=args.media_dir,
            override_fps=args.fps,
            override_resolution=args.resolution,
            dry_run=dry_run,
            jianying_compat=jianying,
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


def _cmd_probe(args: argparse.Namespace) -> int:
    """`fcpxml probe` — media metadata extraction."""
    results = []
    for path in args.videos:
        info = probe_video(path)
        results.append({
            "path": info.path,
            "fps": info.fps,
            "duration_sec": info.duration_sec,
            "total_frames": info.total_frames,
            "width": info.width,
            "height": info.height,
        })

    if args.format == "json":
        payload = results[0] if len(results) == 1 else results
        json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        for r in results:
            print(f"{r['path']}")
            print(f"  Resolution: {r['width']}x{r['height']}")
            print(f"  FPS:        {r['fps']:.4f}")
            print(f"  Duration:   {r['duration_sec']:.2f}s  ({r['total_frames']} frames)")
            print()
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    """`fcpxml validate` — edit script validation."""
    with open(args.script, "r", encoding="utf-8") as f:
        raw = json.load(f)

    script = EditScript.from_dict(raw)
    errors = validate_script(script)

    clip_count = sum(
        1 for t in script.tracks
        for i in t.items if hasattr(i, 'source')
    )

    if not errors:
        summary = {
            "valid": True,
            "title": script.title,
            "tracks": len(script.tracks),
            "clips": clip_count,
            "markers": len(script.markers),
        }
        if args.json:
            json.dump(summary, sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write("\n")
        else:
            print(f"✅ Valid — {summary['tracks']} track(s), {summary['clips']} clip(s), {summary['markers']} marker(s)")
        return 0

    error_count = sum(1 for e in errors if e.severity == "error")
    warning_count = sum(1 for e in errors if e.severity == "warning")

    if args.json:
        json.dump({
            "valid": error_count == 0,
            "errors": [
                {"path": e.path, "message": e.message, "severity": e.severity}
                for e in errors
            ],
        }, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        tag = "❌ INVALID" if error_count > 0 else "⚠️  VALID (warnings)"
        print(f"{tag} — {error_count} error(s), {warning_count} warning(s)")
        for e in errors:
            pfx = "  ❌" if e.severity == "error" else "  ⚠️ "
            print(f"{pfx} {e.path}: {e.message}")

    return 1 if error_count > 0 else 0
