# Agent Integration Guide

How AI agents (Claude Code, Kimi, GPT, etc.) should use `fcpxml-generator`
as part of an automated video editing pipeline.

## Quick Start for Agents

```bash
# 1. Install
pip install fcpxml-generator

# 2. Generate FCPXML from an edit script
fcpxml edit_script.json -o timeline.fcpxml

# 3. Override timeline settings
fcpxml edit_script.json --fps 29.97 --resolution 1920x1080
```

## Complete Pipeline Pattern

```
Video Files → Analysis → Edit Script JSON → fcpxml-generator → .fcpxml → NLE
```

### Step 1: Analyze footage

Use WhisperX (transcription) + a vision model to produce per-clip metadata:

```json
{
  "source": "/videos/clip1.mp4",
  "in": "00:00",
  "out": "00:13",
  "description": "人物在公园散步，阳光明媚",
  "dialogue": "今天的天气真好，我们出来走走..."
}
```

### Step 2: Make editorial decisions

The AI agent selects which segments to include, in what order, and with what
pacing, based on the user's preferences (duration, style, narrative structure).

Output: `edit_script.json`

### Step 3: Generate FCPXML

```bash
fcpxml edit_script.json -o my_vlog.fcpxml
```

### Step 4: Import into NLE

- **剪映专业版**: 文件 → 导入工程 → 选择 `.fcpxml`
- **Final Cut Pro X**: File → Import → XML
- **DaVinci Resolve**: File → Import → Timeline → FCPXML

## Integration with Claude Code

```markdown
## Skill: generate-timeline

1. Read the analyzed footage data from library.json
2. Create an edit_script.json following docs/edit-script-schema.md
3. Run: fcpxml edit_script.json -o timeline.fcpxml
4. Report: "✅ Timeline generated: timeline.fcpxml (import into 剪映)"
```

## Integration with Python Scripts

```python
from fcpxml_generator import generate_fcpxml

edit_script = {
    "title": "My Vlog",
    "clips": [
        {"source": "/videos/a.mp4", "in": "00:00", "out": "00:13"},
        {"source": "/videos/b.mp4", "in": "00:05", "out": "00:20"},
    ],
}

xml_string = generate_fcpxml(edit_script)
with open("output.fcpxml", "w") as f:
    f.write(xml_string)
```

## Programmatic API

```python
from fcpxml_generator.generator import generate_fcpxml, generate_fcpxml_file

# String output (useful for piping, testing, in-memory)
xml_str = generate_fcpxml(edit_script_dict)

# File output (same as CLI)
path = generate_fcpxml_file(
    "edit_script.json",
    output_path="timeline.fcpxml",
    override_fps="29.97",
    override_resolution="1920x1080",
)
```

## Error Handling

The tool exits with code 1 and prints to stderr on error. Common failures:

| Error | Cause | Fix |
|-------|-------|-----|
| `ValueError: no clips` | Empty clips array | Add at least one clip |
| `FileNotFoundError` | edit_script.json not found | Check file path |
| `ffprobe error` | Missing ffprobe or corrupt media | Falls back to defaults (30fps, 1080p) |
| `WARNING: file not found` | Media file path doesn't exist on this machine | Use `--media-dir` or fix paths |

## Environment Requirements

- **Python >= 3.11**
- **ffprobe** (part of FFmpeg) — optional but recommended for accurate timing
  - macOS: `brew install ffmpeg`
  - Ubuntu: `apt install ffmpeg`
  - Without ffprobe: defaults to 30fps / 1920×1080 / 60s duration
