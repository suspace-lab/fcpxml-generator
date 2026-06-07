# FCPXML Generator

> Generate Final Cut Pro X XML (FCPXML 1.9) timeline files from a simple JSON edit script. Designed for AI agents — one command, zero config, import directly into 剪映 / Final Cut Pro / DaVinci Resolve.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](pyproject.toml)

## Why?

AI agents (Claude, Kimi, GPT) are great at **deciding what to cut** — reading transcripts, picking highlights, ordering clips. But they struggle with **producing valid FCPXML** — the arcane XML schema that professional NLEs expect.

**FCPXML Generator** bridges this gap:

```
AI Agent → edit_script.json → fcpxml-generator → .fcpxml → NLE
```

- **Zero runtime dependencies** — only Python stdlib + optional ffprobe
- **One CLI command** — agent-friendly interface
- **FCPXML 1.9 compliant** — tested for compatibility with 剪映专业版
- **Multi-track ready** — architecture supports multiple video/audio tracks

## Quick Start

```bash
# Install (coming to PyPI)
pip install fcpxml-generator

# Or from source
git clone https://github.com/auto-video/fcpxml-generator
cd fcpxml-generator
uv sync
uv run fcpxml --help
```

### Basic Usage

```bash
# Generate FCPXML from an edit script
fcpxml edit_script.json -o my_vlog.fcpxml

# Override timeline settings
fcpxml edit_script.json --fps 29.97 --resolution 1920x1080

# Point to local media copies
fcpxml edit_script.json --media-dir ./local_videos/

# 剪映 compatibility mode (required for 剪映 import)
fcpxml edit_script.json --jianying -o my_vlog.fcpxml

# Generate SRT subtitles & title overlays
fcpxml srt subtitles.json -o my_vlog.srt
```

### Input Format

The tool reads a simple JSON file describing what to include on the timeline:

```json
{
  "title": "My Vlog",
  "clips": [
    {
      "source": "/Volumes/Media/intro.mp4",
      "in": "00:00",
      "out": "00:13"
    },
    {
      "source": "/Volumes/Media/main.mp4",
      "in": "00:05",
      "out": "00:25"
    }
  ]
}
```

See **[docs/edit-script-schema.md](docs/edit-script-schema.md)** for the full schema.

### Import into NLE

After generation, import the `.fcpxml` file:

| NLE | How to Import |
|-----|--------------|
| **剪映专业版** | 文件 → 导入工程 → 选择 `.fcpxml` |
| **Final Cut Pro** | File → Import → XML |
| **DaVinci Resolve** | File → Import → Timeline → FCPXML |

## Programmatic API

```python
from fcpxml_generator import generate_fcpxml

xml_string = generate_fcpxml({
    "title": "My Vlog",
    "clips": [
        {"source": "/videos/a.mp4", "in": "00:00", "out": "00:13"},
    ],
})
with open("output.fcpxml", "w") as f:
    f.write(xml_string)
```

## Project Status

**Beta (v0.1.0)** — Core FCPXML generation is working. Actively testing
with 剪映专业版 import.

- [x] Single timeline with multiple clips
- [x] ffprobe integration for accurate timing
- [x] FCPXML 1.9 compliance (media-rep, 0s format)
- [x] CLI + programmatic API
- [ ] Multi-track audio/video
- [ ] Transition generation
- [ ] Marker export
- [ ] PyPI release

## Competitive Landscape

See **[docs/competitive-analysis.md](docs/competitive-analysis.md)** for a detailed
comparison, but the TL;DR:

| Tool | Language | JSON→FCPXML | Multi-track | Agent CLI |
|------|----------|------------|-------------|-----------|
| `@bbc/fcpx-xml-composer` | JS | ✅ | ❌ | ❌ |
| OpenTimelineIO fcpx_xml | Python | ⚠️ buggy | ✅ | ❌ |
| `fcpxml` (PyPI) | Python | ❌ read-only | — | — |
| **fcpxml-generator** (us) | Python | ✅ | ✅ | ✅ |

We are the **only Python CLI tool** that takes a JSON edit script and produces
FCPXML 1.9 output suitable for 剪映 import. No existing open-source tool fills
this gap.

## Feedback & Bug Reports

If something doesn't work as expected, please help us improve!

Create a Markdown file in the **[`feedback/`](feedback/)** directory describing
your issue. See [`feedback/README.md`](feedback/README.md) for the template
and naming convention. The maintainer reviews this directory regularly and
will address your reports.

## Requirements

- **Python ≥ 3.11**
- **ffprobe** (from FFmpeg) — optional but recommended
  - macOS: `brew install ffmpeg`
  - Ubuntu: `apt install ffmpeg`

## Development

```bash
# Setup
uv sync

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=fcpxml_generator

# Run CLI from source
uv run fcpxml edit_script.json -o output.fcpxml
```

## License

MIT — see [LICENSE](LICENSE) file.

## Related Projects

- [auto-video](https://github.com/auto-video) — the parent project (AI-powered video analysis & editing)
- [OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO) — industry standard timeline interchange
- [ButterCut](https://github.com/barefootford/buttercut) — AI video editing with Claude Code
- [@bbc/fcpx-xml-composer](https://github.com/bbc/fcpx-xml-composer) — BBC's JSON→FCPXML (JavaScript)
