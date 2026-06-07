---
name: fcpxml-generate
description: Generate FCPXML 1.9 timeline + SRT subtitles from edit scripts. Importable into 剪映专业版, Final Cut Pro X, and DaVinci Resolve.
---

# Generate FCPXML Timeline & SRT Subtitles

Use this skill whenever the user asks to:
- "generate a timeline" / "create an FCPXML" / "export to 剪映"
- "make an edit timeline" / "produce a project file"
- "add subtitles" / "generate captions" / "export SRT"
- "create a rough cut" / "export edit decision"

## Prerequisites

The `fcpxml` CLI tool must be installed:
```bash
pip install fcpxml-generator
# or: uv tool install fcpxml-generator
```

Verify:
```bash
fcpxml --version
```

## Workflow

### Step 1: Gather footage metadata

```bash
fcpxml probe video1.mp4 video2.mp4 --format json
```

Returns: `path`, `fps`, `duration_sec`, `total_frames`, `width`, `height`.

### Step 2: Analyze footage

Use transcription (WhisperX) + visual analysis. Produce per-clip metadata:
- `description`: what's happening
- `dialogue`: transcript or summary
- `in`/`out`: timecode boundaries

### Step 3: Make editorial decisions

Consider: duration target, pacing, narrative structure, audio tracks.

### Step 4: Write the edit script

Create `edit_script.json`. **Multi-track format (recommended):**
```json
{
  "title": "My Vlog",
  "tracks": [
    {
      "name": "V1", "role": "video",
      "items": [
        {"type": "clip", "source": "/path/video.mp4", "in": 0, "out": 13},
        {"type": "gap", "duration": 2},
        {"type": "clip", "source": "/path/video2.mp4", "in": 5, "out": 20}
      ]
    },
    {
      "name": "A1", "role": "audio",
      "items": [
        {"type": "clip", "source": "/path/music.mp3", "in": 0, "out": 60}
      ]
    }
  ],
  "markers": [
    {"name": "Chapter 1", "time": 0, "color": "Blue"}
  ]
}
```

Flat format (backward compat):
```json
{
  "title": "My Vlog",
  "clips": [
    {"source": "/path/video.mp4", "in": "00:00", "out": "00:13"}
  ]
}
```

### Step 5: Write subtitles & title overlays

Create `subtitles.json`. See `docs/srt-schema.md` for full spec.
```json
[
  {"text": "今天天气真好",     "start": 0, "end": 3, "type": "subtitle"},
  {"text": "第一章：出发",     "start": 3, "end": 6, "type": "title"},
  {"text": "我们去散步吧",     "start": 6, "end": 9, "type": "subtitle"}
]
```

- `"type": "subtitle"` — dialogue captions (bottom of screen)
- `"type": "title"` — decorative title overlays / 花字 (styled in 剪映)
- Time values: float seconds or `"HH:MM:SS,mmm"` SRT timecode

### Step 6: Validate

```bash
fcpxml validate edit_script.json
```

### Step 7: Generate

```bash
# 剪映 (recommended — uses flattening for 剪映 compatibility)
fcpxml generate edit_script.json --jianying -o vlog.fcpxml

# FCPX / DaVinci Resolve (default — preserves connected-clip structure)
fcpxml generate edit_script.json -o vlog.fcpxml

# Dry-run preview
fcpxml generate edit_script.json --jianying --dry-run

# Override timeline settings
fcpxml generate edit_script.json --jianying --fps 29.97 --resolution 1920x1080 -o vlog.fcpxml

# Generate SRT
fcpxml srt subtitles.json -o vlog.srt
```

### Step 8: Report to user

```
✅ Generated:
  - vlog.fcpxml (timeline)
  - vlog.srt (3 cues: 2 subtitles, 1 title)

Import into 剪映专业版:
  1. 文件 → 导入工程 → 选择 vlog.fcpxml
  2. 拖入 vlog.srt → 自动识别字幕轨
  3. 花字条目换样式: 选中 → 文本 → 花字模板

Timeline summary:
  - Duration: ~2m 34s
  - Clips: 15 across 2 tracks (V1, A1)
  - Subtitles: 24 cues
  - Titles: 3 cues
  - Markers: 3 chapter markers
```

## Important Rules

1. **Always validate before generating.** `fcpxml validate` first.
2. **剪映 → `--jianying`**. Always use `--jianying` when targeting 剪映. 剪映 does NOT understand `<connected-clip>` — without this flag, secondary tracks are lost.
3. **Absolute paths** for all `source` fields. Relative paths cause import failures.
4. **Time values**: new format uses float seconds (0, 13.5). Old format uses "MM:SS" strings.
5. **Error handling**: read stderr carefully — it tells you which clip has the problem.
6. **Report issues**: create `.md` in `feedback/` directory. See `feedback/README.md`.
