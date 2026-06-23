# OmniSight — AI Visual Conversation Assistant

> 基于浏览器的 AI 视觉对话助手 + 企业海面助手。打开摄像头和麦克风，让 AI 看到你的世界、听到你的声音，并给予自然的语音回应。上传 JD 和简历，AI 自动生成结构化面试题库并进行全流程面试。

## 🎬 Demo

[![OmniSight Demo](https://img.shields.io/badge/百度网盘-演示视频-blue?logo=baidu)](https://pan.baidu.com/s/1UNnn_tBrFyF6Tuw2xXaHlA?pwd=9sdb)

**提取码**: `9sdb`

> ⚠️ 百度网盘在线预览会压缩画质，**请下载到本地观看**以获得完整清晰度。

> 演示内容：实时视频对话、Canvas 流场粒子背景、玻璃态按钮、自然语音交互

## 特性

- 🎥 **摄像头视觉理解** — AI 实时查看摄像头画面，理解场景内容
- 🎤 **语音对话** — 像聊天一样说话，AI 听懂并回应
- 🧠 **多轮记忆** — AI 记住对话上下文，连续交流不丢失
- 🤖 **Agent 系统** — 可扩展的 Agent 框架，支持多场景 AI 人格
- 📄 **文档解析** — 上传 JD + 简历（PDF/DOCX），AI 自动提取实体并匹配
- 📋 **AI 题库** — 基于 JD/简历/技能缺口自动生成结构化面试题库
- 🎯 **STAR 面试** — AI 面试官遵循 STAR 法则进行结构化追问
- 📊 **雷达评分** — 面试后 5 维雷达评分 + AI 决策报告
- 🎨 **流场粒子背景** — Canvas 粒子系统 + 鼠标交互，随对话状态变色
- 🪟 **玻璃态 UI** — 磨砂玻璃按钮 + 渐变边缘光环
- 🔊 **高品质 TTS** — sherpa-onnx 引擎（vits-melo-tts-zh_en），中文清晰自然
- 🏠 **本地优先** — 默认使用本地 AI 模型（Ollama），数据不离开本机
- ⚡ **实时交互** — 支持打断、流式输出、低延迟响应
- 🔌 **双引擎** — Ollama 本地模型 / 阿里云百炼云端模型自由切换

## 前置要求

- **Python >=3.11**（通过 `uv` 管理）
- **Node.js >=20.15.0**
- **[Ollama](https://ollama.com/)** 并拉取视觉模型：
  ```bash
  ollama pull qwen3.5:2b-bf16
  ```
- **（可选）阿里云百炼 API Key**：使用云端模型或面试场景时，在 `.env` 配置：
  ```env
  AI_PROVIDER=bailian
  BAILIAN_API_KEY=sk-xxxxxxxxxxxxxxxx
  BAILIAN_MODEL=qwen3.5-omni-plus
  ```

## 快速开始

```bash
# 1. 一键安装
scripts\setup.bat

# 2. 下载 TTS 模型
powershell -ExecutionPolicy Bypass -File scripts\download-sherpa-tts.ps1

# 3. 配置环境变量（可选 — 默认使用 Ollama 本地模型）
#    复制 .env.example 为 .env，填入百炼 API Key（如需要）

# 4. 启动后端（新终端）
scripts\run-backend.bat

# 5. 启动前端（新终端）
scripts\run-frontend.bat

# 6. 打开浏览器
# http://localhost:5173
```

## 项目结构

```
OmniSight/
├── docs/               # 项目文档（需求、架构、技术栈、Agent开发指南）
├── dev-logs/           # 开发日志
├── backend/            # Python FastAPI 后端
├── frontend/           # React + TypeScript 前端
└── scripts/            # 启动/安装脚本
```

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 19, TypeScript, Vite, Canvas API, vitest |
| 后端 | Python 3.11+, FastAPI, WebSocket |
| AI 模型 | Ollama (qwen3.5:2b-bf16) + 阿里云百炼 (qwen3.5-omni-plus) 双引擎 |
| STT | faster-whisper (small / base) |
| TTS | sherpa-onnx (vits-melo-tts-zh_en) |
| VAD | Silero VAD (@ricky0123/vad-web) |
| 文档解析 | pdfplumber + python-docx |

详见 [docs/tech-stack.md](docs/tech-stack.md)

## Agent 系统

OmniSight 内置可扩展的 Agent 框架，不同 Agent 拥有独立的系统提示词和 UI 配置：

| Agent | ID | 场景 | UI 特性 |
|-------|-----|------|---------|
| **视觉聊天伴侣** | `chat` | 日常视觉对话 | 摄像头 + 对话面板 |
| **企业海面助手** | `interview` | 结构化面试 | 📄 文档上传 · 📋 AI 题库 · 🎯 STAR 追问 · 📊 雷达评分 |

详见 [docs/agent-framework.md](docs/agent-framework.md) — 如何添加新 Agent。

## 开发进度

| PR | 状态 | 内容 |
|----|------|------|
| 1-6 | ✅ | 骨架 → WS 管道 → AI 核心 → TTS+打断 → 健壮性 → 设计系统 |
| 7 | ✅ | TTS 引擎升级：sherpa-onnx 替代 Piper |
| 8 | ✅ | 系统提示词 + 多轮对话记忆 + 沉浸式体验 |
| 9 | ✅ | Canvas 流场粒子背景 + GlassButton 玻璃态按钮 |
| 10 | ✅ | AI Provider 抽象层 + 阿里云百炼 HTTP 集成 |
| 11 | ✅ | Agent 框架 + Agent 选择器 UI |
| 12 | ✅ | 文档解析（PDF/DOCX）+ 实体提取（技能/经验/学历） |
| 13 | ✅ | InterviewAgent 面试前：文档上传 + 动态题库生成 |
| 14 | ✅ | InterviewAgent 面试中：全双工语音 + STAR 追问 |
| 15 | ✅ | InterviewAgent 面试后：雷达评分 + AI 决策报告 |
| 16 | ✅ | 端到端集成测试 + 文档完善 |

**当前版本**: v0.10.0

## 开发

本项目遵循 PR 驱动开发流程，详见 [.claude/rules/commit_pr_rule.md](.claude/rules/commit_pr_rule.md)。

- 📋 [需求文档](docs/requirements.md)
- 🏗 [系统架构](docs/architecture.md)
- 📝 [实施步骤](docs/implementation-steps.md)
- 🎨 [设计系统](docs/design-system.md)
- 🤖 [Agent 框架](docs/agent-framework.md)
- 📊 [开发日志](dev-logs/INDEX.md)

## License

MIT
