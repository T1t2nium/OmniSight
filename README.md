# OmniSight — AI Visual Conversation Assistant

> 基于浏览器的 AI 视觉对话助手。打开摄像头和麦克风，让 AI 看到你的世界、听到你的声音，并给予自然的语音回应。

## 特性

- 🎥 **摄像头视觉理解** — AI 实时查看摄像头画面，理解场景内容
- 🎤 **语音对话** — 像聊天一样说话，AI 听懂并回应
- 🏠 **本地优先** — 默认使用本地 AI 模型（Ollama），数据不离开本机
- ⚡ **实时交互** — 支持打断、流式输出、低延迟响应
- 🔌 **可切换后端** — Ollama 本地模型 / Gemini 云端 API 一键切换

## 前置要求

- **Python >=3.11**（通过 `uv` 管理）
- **Node.js >=20.15.0**
- **[Ollama](https://ollama.com/)** 并拉取视觉模型：
  ```bash
  ollama pull gemma3:12b
  # 或
  ollama pull llava:13b
  ```

## 快速开始

```bash
# 1. 一键安装
scripts\setup.bat

# 2. 启动后端（新终端）
scripts\run-backend.bat

# 3. 启动前端（新终端）
scripts\run-frontend.bat

# 4. 打开浏览器
# http://localhost:5173
```

## 项目结构

```
OmniSight/
├── docs/               # 项目文档（需求、架构、技术栈）
├── dev-logs/           # 开发日志
├── backend/            # Python FastAPI 后端
├── frontend/           # React + TypeScript 前端
└── scripts/            # 启动/安装脚本
```

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 19, TypeScript, Vite |
| 后端 | Python 3.11+, FastAPI, WebSocket |
| AI 模型 | Ollama (gemma3 / LLaVA) |
| STT | faster-whisper |
| TTS | 浏览器 SpeechSynthesis → Piper TTS |
| VAD | Silero VAD (@ricky0123/vad-web) |

详见 [docs/tech-stack.md](docs/tech-stack.md)

## 开发

本项目遵循 PR 驱动开发流程，详见 [.claude/rules/commit_pr_rule.md](.claude/rules/commit_pr_rule.md)。

- 📋 [需求文档](docs/requirements.md)
- 🏗 [系统架构](docs/architecture.md)
- 📝 [实施步骤](docs/implementation-steps.md)
- 📊 [开发日志](dev-logs/INDEX.md)

## License

MIT
