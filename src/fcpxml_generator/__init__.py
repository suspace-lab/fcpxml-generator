"""
FCPXML Generator — produce Final Cut Pro X XML (FCPXML 1.9) timeline files.

Designed as a CLI tool for AI agents (Claude, Kimi, GPT, etc.) to generate
video edit timelines that can be imported into:

- 剪映专业版 (JianYing Pro / CapCut)
- Final Cut Pro X
- DaVinci Resolve
- Adobe Premiere Pro (via FCPXML import)

Usage:
    fcpxml input.json -o timeline.fcpxml
    fcpxml input.json --fps 29.97 --resolution 1920x1080

Or programmatically:
    from fcpxml_generator import generate_fcpxml
    generate_fcpxml("input.json", "output.fcpxml")
"""

__version__ = "0.1.0"
