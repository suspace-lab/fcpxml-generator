# Feedback & Bug Reports

遇到使用不顺畅的地方？发现 bug？有功能需求？

请在本目录下创建一个 `.md` 文件，描述你遇到的问题或期望的功能。

## 命名格式

```
YYYY-MM-DD-简短描述.md
```

例如：
- `2026-06-06-剪映导入后素材离线.md`
- `2026-06-07-29.97fps时间码偏移.md`
- `2026-06-08-wishlist-支持转场效果.md`

## 内容模板

```markdown
# 标题（一句话概括）

## 环境
- OS: macOS 15 / Windows 11
- Python: 3.11.5
- fcpxml-generator: 0.1.0
- 目标 NLE: 剪映专业版 6.x / FCP 11.0

## 复现步骤

1. 准备 edit_script.json：
   ```json
   { ... }
   ```
2. 运行命令：
   ```bash
   fcpxml generate edit_script.json -o output.fcpxml
   ```
3. 在 剪映 中导入 output.fcpxml
4. 观察到的问题：...

## 期望行为

描述你期望的正确行为是什么样的。

## 实际行为

描述实际发生了什么。

## 附加信息

- 截图、日志、生成的 .fcpxml 文件片段等
```

## 流程

1. 用户在本目录创建 Markdown 文件描述问题
2. 开发者定期查阅本目录
3. 问题被确认后转为正式 Issue 或直接修复
4. 修复后在该 Markdown 文件末尾追加处理结果
