---
name: novel-to-tts-json
description: "将 TXT 小说逐章转换为 Fish Audio S2.1 Pro 有声书 JSON 脚本。触发：用户说转有声书/做有声书/TTS/转换脚本/下一章/继续转/接着做/接着转有声书，以及提到 Fish Audio、txt 转 json、小说转语音。续接上次进度也触发。"
---

# 小说转 TTS 有声书 JSON

逐章将 TXT 小说转换为 Fish Audio S2.1 Pro 兼容的 JSON 脚本。每章转换后跑 **fidelity gate** —— 比对 TXT 末句与 JSON 末句，确保零台词遗漏。

## 前置

确认输入文件夹路径与输出目录（默认在输入文件夹下创建 `output/`）。加载 [`references/fish-audio-prompt.md`](references/fish-audio-prompt.md) —— 完整的转换规范，每章转换前必须读取。

首次转换或续接时，用 `scripts/chapter_tools.py progress load <输出目录>` 检查之前进度。有 `progress.json` → 从上次中断处继续，向用户确认；无 → 从头开始。

## 步骤

### 1. 章节扫描

用 `scripts/chapter_tools.py list <txt目录> <output目录>` 扫描章节文件及其转换状态。

如果 TXT 未切分，先用 `scripts/chapter_tools.py split <txt路径> <输出目录>` 切分。如果用户已有按章切分的 TXT 文件（如 `各章拆分` 目录），跳过切分，直接列出。

**完成标准**：知道总共有几章、哪些已转、哪些待转。

### 2. 逐章转换

从下一个未转换章节开始，读取纯文本，按 `references/fish-audio-prompt.md` 规范转换，输出纯 JSON。

红线（完整规则见参考文件）：

- **speaker 归属**：引号外→旁白，引号内→角色（去引号）
- **夹心句式必须拆分**：台词A → 旁白动作 → 台词B
- **content ≤120 汉字**：超长在标点处断开
- **delay 默认值**：旁白 800、对话 500、转折 1500、场景切换 2000
- **纯 JSON 输出**：无 markdown 标记

**完成标准**：JSON 可解析，含 `character_map` + `script`，每条含四字段。

### 3. fidelity gate

用 `scripts/chapter_tools.py check <章节txt> <json>` 验证：

- **硬失败**（需重试）：末句关键词重叠率 <30%、字段缺失/多余、content 超 120 汉字
- **警告**（不阻断）：台词数量偏差 >2 但末句重叠率 ≥30%——通常由角色长篇叙述嵌套引号造成，属正常现象

硬失败 → 重试最多 2 次，在转换指令中追加"上次转换可能遗漏结尾，请确保从第一个字到最后一个字完整覆盖"。仍失败则标记。
警告 → 直接通过，备注原因。

**完成标准**：该章无硬失败，或已用尽重试并标记。

### 4. 保存与进度

每章 JSON 保存为 `{小说名}_{序号:03d}_{章节标题}.json`，写入输出目录。保存后用 `scripts/chapter_tools.py progress save <输出目录> <序号> <标题>` 更新断点。

全部完成后输出报告：

| 章节 | 状态 | 备注 |
|------|------|------|

状态：✓通过 / ✗未通过 / ⚠警告通过 / ⊘重试后通过。

**完成标准**：所有章节已处理，进度已更新，报告已展示。
