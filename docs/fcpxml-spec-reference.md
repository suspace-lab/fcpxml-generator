# FCPXML 1.9 Specification Reference

Key details of the Apple FCPXML 1.9 format, drawn from
[Apple's official documentation](https://developer.apple.com/documentation/professional-video-applications/fcpxml-reference).

## Document Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<fcpxml version="1.9">
  <resources>
    <format id="r0" name="..." frameDuration="..." width="..." height="..."/>
    <asset id="r1" name="..." src="file://..." start="0s" duration="..."
           hasVideo="1" hasAudio="1" audioSources="1" audioChannels="2" format="r0">
      <media-rep kind="original-media" src="file://..."/>
    </asset>
  </resources>
  <library>
    <event name="...">
      <project name="...">
        <sequence format="r0" duration="..." tcStart="0s" tcFormat="NDF">
          <spine>
            <asset-clip name="..." ref="r1"
                        offset="0s" duration="..." start="0s" tcFormat="NDF"/>
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>
```

## Critical Requirements We Observed

### 1. `<media-rep>` is mandatory inside `<asset>`

Every `<asset>` element MUST contain a `<media-rep>` child element.

**Correct:**
```xml
<asset id="r1" name="clip.mp4" src="file:///Volumes/clip.mp4" ...>
    <media-rep kind="original-media" src="file:///Volumes/clip.mp4"/>
</asset>
```

**Incorrect (will cause import failures in 剪映/FCPX):**
```xml
<asset id="r1" name="clip.mp4" src="file:///Volumes/clip.mp4" .../>
```

### 2. Zero time values must be `0s`, not `0/30000s`

While `0/30000s` is mathematically equivalent to `0s`, many parsers
(including 剪映) expect the canonical form `0s` for zero values.

**Correct:** `offset="0s"`, `start="0s"`
**Incorrect:** `offset="0/30000s"`, `start="0/30000s"`

### 3. Time encoding by frame rate

| fps | frameDuration | N frames → time string |
|-----|--------------|----------------------|
| 29.97 | `1001/30000s` | N × 1001/30000s |
| 30 | `100/3000s` | N × 100/3000s |
| 25 | `100/2500s` | N × 100/2500s |
| 23.976 | `1001/24000s` | N × 1001/24000s |
| 24 | `100/2400s` | N × 100/2400s |
| 59.94 | `1001/60000s` | N × 1001/60000s |
| 60 | `100/6000s` | N × 100/6000s |

### 4. Format name convention

Format names follow the pattern: `FFVideoFormat{width}x{height}p{fps_suffix}`

| Resolution | Format base name |
|-----------|-----------------|
| 3840×2160 | `FFVideoFormat3840x2160` |
| 1920×1080 | `FFVideoFormat1920x1080` |
| 1280×720  | `FFVideoFormat1280x720` |

### 5. Clip timing semantics

```
offset   = position on the timeline
start    = in-point within the source media
duration = how long this clip plays

Example:
  <asset-clip offset="30s" start="10s" duration="20s"/>
  → Appears at 30s on timeline, uses source from 10s-30s (20s)
```

## Differences from FCP 7 XML (XMEML)

| Aspect | FCPXML (FCP X) | XMEML (FCP 7) |
|--------|---------------|---------------|
| Root element | `<fcpxml version="1.9">` | `<xmeml version="5.0">` |
| Timeline model | Spine / storyline | Track-based |
| Main clip element | `<asset-clip>` | `<clipitem>` |
| Time unit | Rational seconds | Integer frames |
| Media reference | `<asset>` + `<media-rep>` | `<file>` + `<pathurl>` |

## NLE Import Compatibility

| NLE | FCPXML 1.9 Support |
|-----|-------------------|
| 剪映专业版 (JianYing Pro) | ✅ Import supported (basic edits + text + speed) |
| Final Cut Pro X 10.5+ | ✅ Native |
| DaVinci Resolve 18+ | ✅ Import supported |
| Adobe Premiere Pro | ⚠️ Via FCP XML import (some features may be lost) |

## References

- [Apple FCPXML Reference](https://developer.apple.com/documentation/professional-video-applications/fcpxml-reference)
- [Creating FCPXML Documents](https://developer.apple.com/documentation/professional-video-applications/creating-fcpxml-documents)
