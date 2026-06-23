# AI Visual Conversation Assistant — 技术栈说明

## 概述

本项目采用前后端分离架构。前端为 React SPA（单页应用），后端为 Python FastAPI 服务，两者通过 WebSocket 进行实时双向通信。

---

## 环境管理

### Python 环境

使用 **[uv](https://github.com/astral-sh/uv)** 管理 Python 虚拟环境和依赖。

```bash
uv venv --python 3.11    # 创建 Python 3.11 虚拟环境
uv pip install <pkg>     # 安装包
uv sync                  # 按 pyproject.toml 同步依赖
```

**Python 版本**: >=3.11（支持 PyTorch 2.x 和所有现代 ML 库）

### Node.js 环境

使用 npm 管理前端依赖。Node >=20.15.0。

---

## 前端技术栈

| 技术 | 版本 | 用途 | 选择理由 |
|------|------|------|---------|
| **React** | ^19.2 | UI 框架 | 生态丰富，hooks 模式适合实时数据流 |
| **TypeScript** | ~5.8 | 类型安全 | 减少运行时错误，提升开发体验 |
| **Vite** | ^6.3 | 构建工具 | 极快的 HMR，原生 ESM，WS 代理配置简单 |
| **@vitejs/plugin-react** | ^4.4 | React 支持 | Vite 官方 React 插件 |
| **@ricky0123/vad-web** | ^0.0.29 | 浏览器端 VAD | Silero VAD 浏览器封装，ONNX Runtime WASM |

### 浏览器 API

| API | 用途 |
|-----|------|
| `navigator.mediaDevices.getUserMedia()` | 摄像头 + 麦克风采集 |
| `WebSocket` | 实时双向通信 |
| `AudioContext` / Web Audio API | 音频播放控制 |
| `window.speechSynthesis` | 浏览器内置 TTS（初版） |
| `MediaStream` / `<video>` | 摄像头预览 |

---

## 后端技术栈

| 技术 | 用途 | 选择理由 |
|------|------|---------|
| **FastAPI** | Web 框架 | 原生 WebSocket 支持、异步、自动 OpenAPI |
| **uvicorn[standard]** | ASGI 服务器 | 高性能，原生 WebSocket（通过 websockets 库） |
| **openCV-python** | 视频帧处理 | JPEG 编解码、图像缩放 |
| **Pillow** | 图像处理 | 轻量图像缩放和格式转换 |
| **numpy** | 数值运算 | 音频/图像数据处理基础 |
| **pydantic** | 数据验证 | FastAPI 原生支持，类型安全 |
| **python-dotenv** | 环境配置 | .env 文件管理 |
| **httpx** | HTTP 客户端 | 异步 HTTP，调用 Ollama / 百炼 API |
| **pydantic-settings** | 环境配置 | .env 文件加载与验证 |

### AI/ML 相关

| 技术 | 用途 | 选择理由 |
|------|------|---------|
| **Ollama** | 本地模型运行器 | Windows 原生支持，HTTP API，自动管理模型 |
| **阿里云百炼 DashScope** | 云端多模态模型 | qwen3.5-omni-plus，HTTP SSE 流式，视觉+语音一体化 |
| **faster-whisper** | 语音转文字 | CTranslate2 加速，比 OpenAI Whisper 快 4x，支持 CPU/CUDA |
| **torch** | PyTorch 运行时 | faster-whisper 依赖，模型推理 |
| **modelscope** | 模型下载（魔搭） | 国内满速下载 faster-whisper 模型，HuggingFace 自动 fallback |
| **piper-tts** (后备) | 本地 TTS（后备选项） | ONNX Runtime，Windows 兼容，轻量 |
| **sherpa-onnx** (默认) | 本地 TTS（默认引擎） | matcha-icefall-zh-baker，内置中文 FST+词典，Apache 2.0 |

### Agent 框架

| 技术 | 用途 | 选择理由 |
|------|------|---------|
| **BaseAgent (ABC)** | Agent 抽象协议 | 零依赖，定义 agent_id/name/description/system_prompt |
| **AgentRegistry** | Agent 注册表 | 类方法单例，注册/查找/列表 |
| **ChatAgent** | 默认 Agent | 视觉聊天伴侣，复用已有 SYSTEM_PROMPT |
| **InterviewAgent** | 面试 Agent | 企业海面助手，三阶段管线（前/中/后） |

### 文档与面试套件

| 技术 | 用途 | 选择理由 |
|------|------|---------|
| **pdfplumber** | PDF 文本提取 | 纯 Python，表格支持，中文兼容 |
| **python-docx** | DOCX 文本提取 | 标准库，轻量 |
| **websockets** | 百炼 Realtime WS 客户端 | 纯 Python，无 C 扩展，>=14.0 |

### 可选云端备选

| 技术 | 用途 |
|------|------|
| **google-genai** | Gemini Live API（云端备选） |

### 后端服务总览

| 服务 | 职责 |
|------|------|
| `document_parser.py` | PDF/DOCX 文本提取 |
| `entity_extractor.py` | JD/简历规则实体提取 + 加权技能匹配 |
| `question_generator.py` | AI 驱动的结构化面试题库生成 |
| `interview_engine.py` | 面试中 instructions 构建 |
| `interview_scorer.py` | AI 五维评分 + 决策报告生成 |
| `bailian_ws_client.py` | 百炼 Realtime WebSocket 客户端（备用） |

---

## 通信协议

### WebSocket 消息格式

所有消息为 JSON，包含 `type` 字段区分消息类型。

**浏览器 → 服务器**：
```json
{"type": "audio_chunk", "data": "<base64 pcm16>", "timestamp": 1234567890}
{"type": "video_frame", "data": "<base64 jpeg>", "timestamp": 1234567890, "width": 640, "height": 480}
{"type": "vad_event", "event": "speech_start | speech_end", "timestamp": 1234567890}
{"type": "agent_select", "payload": {"agent_id": "chat"}, "timestamp": 1234567890}
{"type": "reset_conversation", "payload": {}}
{"type": "document_upload", "payload": {"doc_type": "jd|resume", "filename": "...", "data": "<base64>"}}
{"type": "start_interview", "payload": {}}
{"type": "stop_interview", "payload": {}}
```

**服务器 → 浏览器**：
```json
{"type": "server_status", "payload": {"status": "connected"}, "timestamp": 1234567890}
{"type": "agent_list", "payload": {"agents": [{"agent_id": "chat", "name": "视觉聊天伴侣", ...}]}}
{"type": "transcript", "payload": {"text": "用户说的话", "language": "zh", "duration_ms": 2500}}
{"type": "llm_response", "payload": {"delta": "AI 回复内容", "done": false}}
{"type": "tts_audio", "payload": {"data": "<base64 pcm16>", "sample_rate": 44100}}
{"type": "interrupt", "payload": {"reason": "user_interrupt"}}
{"type": "error", "payload": {"message": "错误描述"}}
{"type": "document_parsed", "payload": {"doc_type": "jd|resume", "jd_entities": {...}, "match_result": {...}}}
{"type": "question_bank", "payload": {"categories": [...], "total_questions": 12}}
{"type": "interview_started", "payload": {"phase": "icebreaker"}}
{"type": "interview_stopped", "payload": {"transcript": [...], "message": "..."}}
{"type": "interview_report", "payload": {"scores": {...}, "overall_score": 75, "strengths": [...], ...}}
```

---

## 版本锁定原则

- 主版本号固定（避免 breaking changes）
- 次版本号最小约束（允许补丁更新）
- `uv` 通过 `pyproject.toml` 声明依赖
- npm 通过 `package.json` 声明依赖
