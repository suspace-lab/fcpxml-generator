# Wishlist: 支持 Title / Text Overlay（花字）

## 环境
- OS: macOS 15
- Python: 3.11
- fcpxml-generator: 0.1.0
- 目标 NLE: 剪映专业版

## 需求

需要在 FCPXML 中嵌入文字标题/花字 overlay。使用场景：

1. **场景引导**：在叙事片段的开头添加花字，解释当前场景。如 "📍 出发准备"、"🌾 乡村风光"、"🏠 回到家中"
2. **情绪渲染**：转场处添加氛围文字
3. **章节标题**：视频开始时的标题卡

## 期望的编辑脚本格式

在 EditScript 或 TrackItem 层级增加 `titles` 字段：

```json
{
  "titles": [
    {
      "text": "📍 出发准备",
      "start": 0.0,
      "duration": 3.0,
      "style": "lower-third",
      "font_size": 48,
      "alignment": "center"
    },
    {
      "text": "🌾 乡村风光",
      "start": 15.2,
      "duration": 3.0
    }
  ]
}
```

## FCPXML 实现

FCPXML 1.9 支持 `<title>` 元素嵌入 sequence。例如：

```xml
<title name="Basic Title" lane="1" offset="0s" ref="r2" duration="90/30s" start="3600/30s">
  <text>
    <text-style ref="ts1">Hello World</text-style>
  </text>
</title>
```

参考：Apple FCPXML 1.9 spec 的 Title 章节。

## 优先级

Medium — 当前编辑流程中，叙事引导靠字幕完成。有 title 支持后，Editor Agent 可以自动生成引导花字，大幅提升成片质量。
