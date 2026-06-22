# AI Visual Conversation Assistant — 系统架构

## 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                      Browser (React SPA)                      │
│                                                               │
│  ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐        │
│  │ Camera    │ │ Mic      │ │ VAD      │ │ Audio   │        │
│  │ Preview   │ │ Capture  │ │ Engine   │ │ Player  │        │
│  │ (<video>) │ │(getUM)   │ │(@vad-web)│ │(Web API)│        │
│  └───────────┘ └──────────┘ └──────────┘ └─────────┘        │
│        │              │              │              ▲         │
│        │ video        │ pcm16        │ events       │         │
│        ▼              ▼              ▼              │         │
│  ┌───────────────────────────────────────────────────┐       │
│  │              WebSocket Client                      │       │
│  │    (ws://localhost:8000/ws)                        │       │
│  └───────────────────┬───────────────────────────────┘       │
│                      │                                        │
│  ┌───────────────────┴───────────────────────────────┐       │
│  │  AgentSelector  │  ChatLog  │  ControlBar          │       │
│  │  (胶囊标签)     │ (对话记录) │ (开始/停止/切换)     │       │
│  └───────────────────────────────────────────────────┘       │
└──────────────────────┼───────────────────────────────────────┘
                       │
  audio_chunk / video_frame / vad_event / agent_select
  transcript / llm_response / tts_audio / agent_list
                       │
┌──────────────────────┼───────────────────────────────────────┐
│                      ▼                     Backend (FastAPI)  │
│  ┌───────────────────────────────────────────────────┐       │
│  │              WebSocket Handler (/ws)               │       │
│  │    - Session management + agent routing            │       │
│  │    - Audio buffer per session                      │       │
│  │    - Frame manager (rate limit + motion detection) │       │
│  └───────┬──────────┬──────────────┬──────────────────┘      │
│          │          │              │                          │
│          ▼          ▼              ▼                          │
│  ┌──────────┐ ┌─────────┐ ┌───────────────┐                 │
│  │ Whisper  │ │ Frame   │ │ AgentRegistry │                 │
│  │ STT      │ │ Mgr     │ │ (BaseAgent →  │                 │
│  │(faster-  │ │(resize, │ │  system_prompt)│                │
│  │ whisper) │ │ rate-lmt)│ └──────┬────────┘                 │
│  └────┬─────┘ └────┬────┘        │                           │
│       │ text        │ image       │ system_prompt            │
│       └─────────────┼─────────────┘                          │
│                     ▼                                        │
│           ┌─────────────────┐                               │
│           │  Orchestrator   │                               │
│           │ (Conversation)  │                               │
│           └────────┬────────┘                               │
│                    │                                         │
│                    ▼                                         │
│           ┌──────────────────┐                              │
│           │   AI Provider    │                              │
│           │ ┌──────────────┐ │                              │
│           │ │ Ollama       │ │ ← HTTP /api/chat             │
│           │ │ (gemma3:12b) │ │   localhost:11434            │
│           │ └──────────────┘ │                              │
│           │ ┌──────────────┐ │                              │
│           │ │ Bailian (百炼)│ │ ← HTTP SSE Streaming         │
│           │ │ qwen3.5-omni │ │   dashscope.aliyuncs.com     │
│           │ └──────────────┘ │                              │
│           └────────┬─────────┘                              │
│                    │ text response                           │
│                    ▼                                         │
│           ┌──────────────┐                                  │
│           │     TTS      │                                  │
│           │ sherpa-onnx  │ ← 默认，中文最佳                  │
│           │ Piper (后备) │ ← 子进程封装                      │
│           │ Browser API  │ ← 终极后备                       │
│           └──────────────┘                                  │
└──────────────────────────────────────────────────────────────┘
```

---

## 数据流详解

### 流程 1：用户说话 → AI 回复

```
1. 用户说话
   ↓
2. VAD 检测 speech_start → 开始累积 PCM16 音频
   ↓
3. VAD 检测 speech_end → 发送 vad_event + audio_chunk 到后端
   ↓
4. 后端接收音频 → 存入 session 音频缓冲
   ↓
5. 后端: whisper.transcribe(audio) → 转写文本
   ↓
6. 后端: 查 session.selected_agent → AgentRegistry.get() → 获取 system_prompt
   ↓
7. 后端: ai_client.chat(text=transcript, image=frame, system_prompt=agent.system_prompt) → 流式文本
   ↓
8. 后端: 流式发送 llm_response 到前端
   ↓
9. 前端: 更新 ChatLog + TTS 播放
```

### 流程 2：用户打断 AI

```
1. AI 正在生成/播放回复
   ↓
2. 用户开始说话 → VAD 检测 speech_start
   ↓
3. 前端: 停止音频播放
   ↓
4. 前端 → 后端: 发送 vad_event(speech_start)
   ↓
5. 后端: 取消 AI pipeline → 发送 interrupt → 开始处理新输入
```

### 流程 3：Agent 切换

```
1. 后端 → 前端: agent_list (会话注册后发送)
   ↓
2. 前端: AgentSelector 展示可选 Agent 列表
   ↓
3. 用户点击 → 前端 → 后端: agent_select { agent_id }
   ↓
4. 后端: 存储到 SessionState.selected_agent
   ↓
5. 后续 AI pipeline 使用新 Agent 的 system_prompt
```

### 流程 4：视频帧管理

```
1. 浏览器每 ~200ms 捕获一帧 JPEG（5fps）
   ↓
2. 通过 WebSocket 发送 video_frame 到后端
   ↓
3. frame_manager:
   - 运动检测过滤重复帧
   - 存储最新有效帧（覆盖旧帧）
   - 发送给 AI 时使用最新帧
```

---

## 会话状态模型

```
SessionState
  ├── session_id: str (UUID)
  ├── connected_at: float
  ├── last_activity: float
  ├── frame_count: int
  ├── audio_chunk_count: int
  ├── audio_duration_ms: float
  ├── latest_frame: str | None      # base64 JPEG，每次 video_frame 覆盖
  ├── latest_frame_timestamp: float
  ├── ai_status: str                # idle | listening | thinking | speaking
  ├── history: list[dict]           # 多轮对话历史 (PR 8)
  └── selected_agent: str = "chat"  # 当前会话选中的 Agent (PR 11)
```

---

## 组件职责

### 前端组件

| 组件 | 职责 | 依赖 |
|------|------|------|
| App | 根组件，管理全局状态 | 所有 hooks |
| AgentSelector | Agent 选择器（玻璃态胶囊标签） | useAgent |
| VideoPanel | 摄像头预览 | useMediaStream |
| AudioIndicator | VAD + AI 状态指示 | useVAD |
| ChatLog | 对话记录展示 | WebSocket 消息 |
| ConnectionStatus | WS 连接状态 | useWebSocket |
| ControlBar | 控制面板 | useMediaStream, useWebSocket |
| NeuralBackground | Canvas 流场粒子背景 | Canvas API |

### 前端 Hooks

| Hook | 职责 |
|------|------|
| useWebSocket | WebSocket 连接生命周期、消息收发、自动重连 |
| useMediaStream | 摄像头/麦克风采集 |
| useVAD | 浏览器端语音活动检测 |
| useAudioPlayer | PCM16 Web Audio API 播放 + SpeechSynthesis fallback |
| useFrameCapture | 视频帧定时捕获 |
| useAgent | Agent 列表 + 选中状态管理 |

### 后端服务

| 服务 | 职责 |
|------|------|
| ws.py | WebSocket 连接管理、消息路由、Agent 感知会话协调 |
| base_ai_client.py | AI Provider 统一抽象接口 (ABC) |
| ollama_client.py | Ollama HTTP API 调用、NDJSON 流式生成 |
| bailian_http_client.py | 阿里云百炼 DashScope 多模态生成、SSE 流式 |
| conversation.py | 全链路编排：STT → Agent → LLM → TTS |
| agents/base.py | BaseAgent ABC + AgentRegistry 单例 + ChatAgent |
| transcribe.py | faster-whisper 语音转写（ModelScope 下载 + CUDA） |
| sherpa_tts.py | sherpa-onnx TTS（默认，中文最佳质量） |
| tts.py | Piper TTS（子进程后备） |
| audio.py | PCM 缓冲管理 |
| frame_manager.py | 帧缓存、帧率控制、运动检测 |
| prompts.py | 多 Agent 共享 System Prompt 管理 |
