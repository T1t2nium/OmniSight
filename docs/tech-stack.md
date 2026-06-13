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
| **httpx** | HTTP 客户端 | 异步 HTTP，调用 Ollama API |

### AI/ML 相关

| 技术 | 用途 | 选择理由 |
|------|------|---------|
| **Ollama** | 本地模型运行器 | Windows 原生支持，HTTP API，自动管理模型 |
| **faster-whisper** | 语音转文字 | CTranslate2 加速，比 OpenAI Whisper 快 4x，支持 CPU |
| **torch** | PyTorch 运行时 | faster-whisper 依赖，模型推理 |
| **piper-tts** (后备) | 本地 TTS（后备选项） | ONNX Runtime，Windows 兼容，轻量 |
| **kokoro-onnx** (默认) | 本地 TTS（默认引擎） | Kokoro 82M ONNX，100+ 中文音色，Apache 2.0 |
| **soundfile** | 音频文件读写 | kokoro-onnx 依赖 |

### 可选云端备选

| 技术 | 用途 |
|------|------|
| **google-genai** | Gemini Live API（云端备选） |

---

## 通信协议

### WebSocket 消息格式

所有消息为 JSON，包含 `type` 字段区分消息类型。

**浏览器 → 服务器**：
```json
{"type": "audio_chunk", "data": "<base64 pcm16>", "timestamp": 1234567890}
{"type": "video_frame", "data": "<base64 jpeg>", "timestamp": 1234567890, "width": 640, "height": 480}
{"type": "vad_event", "event": "speech_start", "timestamp": 1234567890}
{"type": "vad_event", "event": "speech_end", "timestamp": 1234567890}
```

**服务器 → 浏览器**：
```json
{"type": "server_echo", "message": "received 2500ms audio, 15 frames"}
{"type": "transcript", "text": "用户说的话", "timestamp": 1234567890}
{"type": "response_text", "text": "AI 回复内容", "chunk": true}
{"type": "response_end", "timestamp": 1234567890}
{"type": "error", "message": "错误描述"}
{"type": "interrupt", "timestamp": 1234567890}
```

---

## 版本锁定原则

- 主版本号固定（避免 breaking changes）
- 次版本号最小约束（允许补丁更新）
- `uv` 通过 `pyproject.toml` 声明依赖
- npm 通过 `package.json` 声明依赖
