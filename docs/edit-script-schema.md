# Edit Script JSON Schema

The input format consumed by `fcpxml-generator`. Designed to be simple enough
that any AI agent (Claude, Kimi, GPT) can produce it from a natural-language
editing request.

## Minimal Example

```json
{
  "title": "My First Vlog",
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

## Full Schema

```json
{
  "title": "string (required)",
  "fps": 30.0,
  "resolution": "1920x1080",
  "music_mood": "string (informational only)",
  "total_duration": "string (informational only, e.g. '0:38')",
  "clips": [
    {
      "source": "string (required) — absolute path to media file",
      "filename": "string — display name, defaults to basename of source",
      "in": "string (required) — MM:SS or HH:MM:SS, in-point in source",
      "out": "string (required) — MM:SS or HH:MM:SS, out-point in source",
      "duration": "string — informational, e.g. '0:13'",
      "description": "string — human-readable description of this clip",
      "dialogue": "string — transcription/summary of speech in this clip",
      "transition": "string — informational only, e.g. 'cut', 'fade_in', 'dissolve'"
    }
  ]
}
```

## Field Details

### Top-level

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `title` | string | **Yes** | — | Project name, used for the FCPXML `<project>` and `<event>` names, and as the default output filename |
| `fps` | number | No | auto-detected | Override timeline frame rate. If omitted, uses the most common fps among source clips |
| `resolution` | string | No | auto-detected | Override timeline resolution (`WxH`). If omitted, uses the first clip's resolution |
| `music_mood` | string | No | — | Informational field, not used in FCPXML output |
| `total_duration` | string | No | — | Informational field, not used in FCPXML output |

### Clip

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `source` | string | **Yes** | — | Absolute path to the media file. Must be accessible by ffprobe |
| `filename` | string | No | basename of `source` | Display name in the timeline |
| `in` | string | **Yes** | — | In-point timecode: `MM:SS` or `HH:MM:SS` |
| `out` | string | **Yes** | — | Out-point timecode: `MM:SS` or `HH:MM:SS` |
| `duration` | string | No | — | Informational field |
| `description` | string | No | — | Human-readable description |
| `dialogue` | string | No | — | Speech transcription or summary |
| `transition` | string | No | "cut" | Suggested transition type (informational) |

## Timecode Formats

All timecodes use the format `MM:SS` or `HH:MM:SS`:

```
00:00       → 0 seconds
01:30       → 90 seconds (1 minute 30 seconds)
00:13.50    → 13.5 seconds
01:00:00    → 3600 seconds (1 hour)
```

## Agent Prompt Template

When asking an AI agent to produce an edit script, use a prompt like:

```
Based on the analyzed video footage, produce an edit script JSON file
following the edit-script schema at docs/edit-script-schema.md.

Timeline requirements:
- Target duration: 3-5 minutes
- Pacing: fast and punchy (2-5 second clips)
- Narrative: chronological

Output the JSON to edit_script.json, then run:
  fcpxml edit_script.json -o my_vlog.fcpxml

The resulting .fcpxml file can be imported into 剪映专业版.
```
