---
name: fcpxml-generate
description: Generate an FCPXML 1.9 timeline file from an edit script JSON. Importable into 剪映专业版, Final Cut Pro X, and DaVinci Resolve.
---

# Generate FCPXML Timeline

Use this skill whenever the user asks to:
- "generate a timeline" / "create an FCPXML" / "export to 剪映"
- "make an edit timeline" / "produce a project file for Premiere/FCP/剪映"
- "create a rough cut" / "export edit decision to XML"

## Prerequisites

The `fcpxml` CLI tool must be installed:
```bash
pip install fcpxml-generator
# or: uv tool install fcpxml-generator
```

Verify it's available:
```bash
fcpxml --version
```

## Workflow

### Step 1: Gather footage metadata

Probe all video files to get accurate timing data:
```bash
fcpxml probe video1.mp4 video2.mp4 --format json
```

This gives you: `path`, `fps`, `duration_sec`, `total_frames`, `width`, `height`.

### Step 2: Analyze footage content

Use transcription (WhisperX) and visual analysis to understand what's in
each video. Produce per-clip metadata:
- `description`: what's happening in this segment
- `dialogue`: transcript or summary of speech
- `in`/`out`: timecode boundaries within the source file

### Step 3: Make editorial decisions

Based on the user's preferences (duration, style, narrative), select clips
and arrange them in order. Consider:
- **Duration target**: how long should the final video be?
- **Pacing**: fast (2-5s clips), natural (5-10s), or cinematic (10-20s)
- **Narrative**: chronological, thematic, or hook-driven
- **Audio**: any background music or voiceover tracks?

### Step 4: Write the edit script

Create `edit_script.json` following the schema in `docs/edit-script-schema.md`.

**New multi-track format (recommended):**
```json
{
  "title": "My Vlog",
  "tracks": [
    {
      "name": "V1",
      "role": "video",
      "items": [
        {"type": "clip", "source": "/path/to/video.mp4", "in": 0, "out": 13},
        {"type": "gap", "duration": 2},
        {"type": "clip", "source": "/path/to/video2.mp4", "in": 5, "out": 20}
      ]
    },
    {
      "name": "A1",
      "role": "audio",
      "items": [
        {"type": "clip", "source": "/path/to/music.mp3", "in": 0, "out": 60}
      ]
    }
  ],
  "markers": [
    {"name": "Chapter 1", "time": 0, "color": "Blue"}
  ]
}
```

**Old flat format (backward compatible):**
```json
{
  "title": "My Vlog",
  "clips": [
    {"source": "/path/to/video.mp4", "in": "00:00", "out": "00:13"}
  ]
}
```

### Step 5: Validate the script

```bash
fcpxml validate edit_script.json
```

Fix any errors before proceeding.

### Step 6: Generate FCPXML

```bash
fcpxml generate edit_script.json -o timeline.fcpxml
```

With overrides:
```bash
fcpxml generate edit_script.json -o timeline.fcpxml --fps 29.97 --resolution 1920x1080
```

### Step 7: Report to user

```
✅ Timeline generated: timeline.fcpxml

Import steps:
  - 剪映专业版: 文件 → 导入工程 → 选择 timeline.fcpxml
  - Final Cut Pro: File → Import → XML
  - DaVinci Resolve: File → Import → Timeline → FCPXML

Timeline summary:
  - Duration: ~2m 34s
  - Clips: 15 across 2 tracks (V1, A1)
  - Markers: 3 chapter markers
```

## Important Rules

1. **Always validate before generating.** Run `fcpxml validate` first.
2. **Use absolute paths** for all `source` fields. Relative paths cause import failures.
3. **Time values**: In the new format, use float seconds (0, 13.5, 90.0). In the old format, use "MM:SS" strings.
4. **File existence**: Ensure all `source` paths point to files that exist on the current machine. Use `--media-dir` if the edit script references paths from a different machine.
5. **Error handling**: If `fcpxml generate` fails, read the error message carefully — it will tell you which clip or track has the problem.
6. **Report issues**: If you encounter bugs or friction, create a `.md` file in the `feedback/` directory at the project root. Use the naming convention `YYYY-MM-DD-short-description.md`. See `feedback/README.md` for the template.
