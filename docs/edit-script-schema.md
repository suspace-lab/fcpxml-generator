# Edit Script JSON Schema

The input format consumed by `fcpxml-generator`. Two formats are supported:
the **new multi-track format** (recommended) and the **old flat format**
(backward compatible).

---

## New Multi-Track Format (Recommended)

```json
{
  "title": "My Vlog",
  "fps": 29.97,
  "resolution": "1920x1080",
  "tracks": [
    {
      "name": "V1",
      "role": "video",
      "items": [
        {"type": "clip", "source": "/Volumes/Media/intro.mp4", "in": 0, "out": 13},
        {"type": "gap", "duration": 2},
        {"type": "clip", "source": "/Volumes/Media/main.mp4", "in": 5, "out": 20}
      ]
    },
    {
      "name": "A1",
      "role": "audio",
      "items": [
        {"type": "clip", "source": "/Volumes/Media/bgm.mp3", "in": 0, "out": 35}
      ]
    }
  ],
  "markers": [
    {"name": "Chapter 1", "time": 0, "color": "Blue"},
    {"name": "Highlight", "time": 15, "color": "Red"}
  ]
}
```

Time values in the new format are **float seconds** (not timecode strings).

---

## Old Flat Format (Backward Compatible)

```json
{
  "title": "My Vlog",
  "clips": [
    {
      "source": "/Volumes/Media/intro.mp4",
      "in": "00:00",
      "out": "00:13"
    }
  ]
}
```

Time values in the old format are **timecode strings** (`"MM:SS"` or `"HH:MM:SS"`).

---

## Full Schema Reference

### Top-level

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `title` | string | **Yes** | — | Project name; used for `<project>` and `<event>` names |
| `fps` | number | No | auto | Override timeline frame rate |
| `resolution` | string | No | auto | Override resolution (`"WxH"`), e.g. `"1920x1080"` |
| `tracks` | array | No* | — | New format: array of Track objects |
| `clips` | array | No* | — | Old format: flat array of Clip objects |
| `markers` | array | No | `[]` | Chapter/annotation markers |
| `music_mood` | string | No | — | Informational only |

> *Exactly one of `tracks` or `clips` must be present.

### Track

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `name` | string | No | `"V1"` | Track display name |
| `role` | string | No | `"video"` | `"video"` or `"audio"` |
| `items` | array | **Yes** | — | Ordered list of TrackItem objects |

### TrackItem (Clip)

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `type` | string | No | `"clip"` | Must be `"clip"` |
| `source` | string | **Yes** | — | Absolute path to media file |
| `in` | number | **Yes** | — | In-point in **seconds** (float) |
| `out` | number | **Yes** | — | Out-point in **seconds** (float) |
| `filename` | string | No | basename | Display name on timeline |
| `description` | string | No | — | Human-readable description |
| `dialogue` | string | No | — | Speech transcription |
| `transition` | string | No | `"cut"` | Suggested transition (informational) |

### TrackItem (Gap)

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `type` | string | **Yes** | — | Must be `"gap"` |
| `duration` | number | **Yes** | — | Duration in **seconds** (float) |

### Marker

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `name` | string | **Yes** | — | Marker label |
| `time` | number or string | **Yes** | — | Position in seconds or timecode |
| `color` | string | No | `"Red"` | FCPXML color: Red, Blue, Green, etc. |

### Old-format Clip (for backward compat)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `source` | string | **Yes** | Absolute path |
| `in` | string | **Yes** | Timecode: `"MM:SS"` or `"HH:MM:SS"` |
| `out` | string | **Yes** | Timecode: `"MM:SS"` or `"HH:MM:SS"` |
| `filename` | string | No | Display name |
| `description` | string | No | Informational |
| `dialogue` | string | No | Informational |
| `transition` | string | No | Informational |

---

## Time Formats

**New format** — float seconds:
```
0       → 0 seconds
13.5    → 13.5 seconds
90.0    → 90 seconds (1 minute 30 seconds)
```

**Old format** — timecode strings:
```
"00:00"    → 0 seconds
"01:30"    → 90 seconds
"00:13.50" → 13.5 seconds
"01:00:00" → 3600 seconds
```

---

## Agent Prompt Template

```
Based on the analyzed video footage, produce an edit_script.json
following the schema at docs/edit-script-schema.md.

Timeline requirements:
- Target duration: 3-5 minutes
- Pacing: fast (2-5 second clips)
- Narrative: chronological
- Include a background music track (A1)

Workflow:
1. Probe all video files: fcpxml probe video1.mp4 video2.mp4 --format json
2. Analyze footage content, select clips, write edit_script.json
3. Validate: fcpxml validate edit_script.json
4. Generate: fcpxml generate edit_script.json -o my_vlog.fcpxml
5. Import into 剪映: 文件 → 导入工程 → 选择 .fcpxml
```
