# novel-to-tts-json

将 TXT 小说逐章转换为 [Fish Audio S2.1 Pro](https://fish.audio) 有声书 JSON 脚本的 AI Skill。

**AI 推理驱动**，逐章转换 + **fidelity gate** 末句比对 → 零内容丢失。断点续传，不怕中断。

## 功能

| 功能 | 说明 |
|------|------|
| 📖 章节切分 | 自动识别「第X章/Chapter X」，切成独立文件 |
| 🔄 AI 推理转换 | AI 逐句阅读理解文本，自行识别角色、语气、切分、delay |
| 🛡️ fidelity gate | 每章 TXT 末句 vs JSON 末句关键词比对，硬失败拦截 + 警告分级 |
| 📊 断点续传 | `progress.json` 记录进度，中断后接着来 |
| 📋 批量检查 | 一次性检查全部章节转换质量 |

## 支持的平台

| 平台 | 支持方式 |
|------|----------|
| **WorkBuddy** | 直接安装 skill 包（推荐） |
| **AtomCode** | 兼容 Claude Code 生态，直接放 skills 目录 |
| **MiMo Code** | 兼容 Claude Code 生态，直接放 skills 目录 |
| **任意 AI 工具** | 复制 `references/fish-audio-prompt.md` 作为系统提示词 |

---

## 快速开始

### 前置

- Python 3.8+（仅标准库，零依赖）
- 各平台对应的 AI 工具

---

## 部署教程

### WorkBuddy

1. 下载 skill 包或从本仓库安装
2. 在 WorkBuddy 对话中说：`用 novel-to-tts-json 转换 <txt目录>`
3. 触发词：`转有声书` / `继续转` / `txt 转 json`

---

### AtomCode

AtomCode 兼容 Claude Code 生态，skill 格式完全一致。

**安装**（二选一）：

```bash
# 方式一：全局安装（所有项目可用）
git clone https://github.com/lytssaa/workbuddy-skill-novel-to-tts-json.git ~/.atomcode/skills/novel-to-tts-json

# 方式二：项目级安装（仅当前项目可用）
cd 你的项目目录
mkdir -p .atomcode/skills
git clone https://github.com/lytssaa/workbuddy-skill-novel-to-tts-json.git .atomcode/skills/novel-to-tts-json
```

**使用**：

```bash
# 在 AtomCode 中直接输入（会自动识别 skill）
$novel-to-tts-json 转换 /path/to/各章拆分/

# 或者先在对话中加载规范，再给任务
请按照 novel-to-tts-json skill 的规则，转换以下章节...
```

**验证安装**：在 AtomCode 中输入 `/skills` 或 `$` 查看是否已列出 `novel-to-tts-json`。

---

### MiMo Code

MiMo Code 基于 OpenCode，同样兼容 Claude Code 生态 skill 格式。

**安装**（二选一）：

```bash
# 方式一：全局安装
git clone https://github.com/lytssaa/workbuddy-skill-novel-to-tts-json.git ~/.config/mimocode/skills/novel-to-tts-json

# 方式二：项目级安装
cd 你的项目目录
mkdir -p .mimocode/skills
git clone https://github.com/lytssaa/workbuddy-skill-novel-to-tts-json.git .mimocode/skills/novel-to-tts-json
```

**使用**：

```bash
# 在 MiMo Code 中触发
$nov
el-to-tts-json 转换 /path/to/各章拆分/

# 或通过 /dream 让 AI 自动调用
```

> **注意**：MiMo Code 的 skill 目录路径以官方文档为准。如路径有变，请查阅 [MiMo Code 文档](https://mimo.xiaomi.com/coder)。

---

### 任意 AI 工具（通用方法）

如果使用的工具不支持 `SKILL.md` 格式，可以手动复制提示词：

1. 打开 `references/fish-audio-prompt.md`（完整转换规范）
2. 将其内容作为**系统提示词**发给 AI
3. 再发送 TXT 章节文本
4. AI 会按规范输出 JSON

```bash
# 快速提取规范文本
cat references/fish-audio-prompt.md
```

---

## JSON 输出格式

```json
{
  "character_map": {
    "林廷扬": {
      "gender": "男",
      "age": "中年",
      "role_tag": "重要角色",
      "personality": "安远镖局总镖头，武艺高强，为人正直沉稳。",
      "timbre": "低沉有力，中年男性的沉稳嗓音，略带威严。"
    }
  },
  "script": [
    {
      "speaker": "旁白",
      "content": "夜深人静，官道上马蹄声急。",
      "emo_vector": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
      "delay": 800
    }
  ]
}
```

字段约束：
- `character_map`：5 个字段（gender/age/role_tag/personality/timbre）
- `script` 每条：speaker / content / emo_vector / delay
- `content`：≤120 汉字，超长在标点处断开
- `emo_vector`：**固定 8 元素数组** `[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]`

## 核心设计

### AI 推理 vs 脚本生成

本 skill 的核心是 **AI 推理**，不是模板拼接：

- ✅ AI 逐句阅读理解文本，自行判断角色归属、语气、切分
- ✅ 每个 TXT 独立处理，不需要参照已有 JSON
- ❌ 禁止编写 Python 脚本批量生成 JSON

## 文件结构

```
novel-to-tts-json/
├── SKILL.md                          # 主 skill 文件（AtomCode/MiMo Code 通用）
├── references/
│   └── fish-audio-prompt.md          # 完整转换规范（可单独作为提示词使用）
├── scripts/
│   └── chapter_tools.py              # 切分 + fidelity gate + 进度工具
└── README.md
```

## License

MIT
