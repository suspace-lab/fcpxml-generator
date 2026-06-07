# SRT Subtitle & Title Overlay Schema

Input format for `fcpxml srt`. Produces standard SRT files importable
into 剪映, Final Cut Pro, Premiere Pro, and any NLE with SRT support.

## Minimal Example

```json
[
  {"text": "今天天气真好", "start": 0, "end": 3}
]
```

## Full Schema

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `text` | string | **Yes** | — | Subtitle/title text content |
| `start` | number or string | **Yes** | — | Float seconds or `"HH:MM:SS,mmm"` |
| `end` | number or string | **Yes** | — | Float seconds or `"HH:MM:SS,mmm"` |
| `type` | string | No | `"subtitle"` | `"subtitle"` or `"title"` (informational) |

## Time Formats

```
1.5                  → float seconds
"00:00:01,500"       → SRT timecode (comma)
"00:00:01.500"       → SRT timecode (dot)
"01:30"              → MM:SS
"01:00:00"           → HH:MM:SS
```

## Type Field

| Type | Use | 剪映 Styling |
|------|-----|-------------|
| `"subtitle"` | Dialogue captions | Bottom, standard font |
| `"title"` | Chapter titles / 花字 | Centered, decorative |

Both produce identical SRT. The `type` is semantic labeling for the
AI agent. User applies styling in 剪映 after import.

## Complete Example

```json
[
  {"text": "今天天气真好",       "start": 0,    "end": 3,   "type": "subtitle"},
  {"text": "第一章",             "start": 3,    "end": 6,   "type": "title"},
  {"text": "我们出发吧",         "start": 6,    "end": 9,   "type": "subtitle"},
  {"text": "B-Roll: 航拍镜头",   "start": 3.5,  "end": 5.5, "type": "title"}
]
```

## Dict Wrapper

Also accepts:
```json
{"subtitles": [{"text": "Hello", "start": 0, "end": 2}]}
```

## Agent Workflow

```bash
fcpxml srt subtitles.json -o output.srt
fcpxml generate edit_script.json --jianying -o vlog.fcpxml
# → delivers vlog.fcpxml + vlog.srt
```
