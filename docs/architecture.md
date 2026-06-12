# AI Visual Conversation Assistant — 系统架构

## 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                      Browser (React SPA)                 │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ Camera   │  │ Mic      │  │ VAD      │  │ Audio   │ │
│  │ Preview  │  │ Capture  │  │ Engine   │  │ Player  │ │
│  │ (<video>)│  │(getUM)   │  │(@vad-web)│  │(Web API)│ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │
│        │             │              │              ▲     │
│        │ video       │ pcm16        │ events       │     │
│        ▼             ▼              ▼              │     │
│  ┌──────────────────────────────────────────────────┐   │
│  │              WebSocket Client                     │   │
│  │    (ws://localhost:8000/ws)                       │   │
│  └──────────────────┬───────────────────────────────┘   │
└─────────────────────┼────────────────────────────────────┘
                      │
        audio_chunk / video_frame / vad_event
        response_text / audio / interrupt
                      │
┌─────────────────────┼────────────────────────────────────┐
│                     ▼                  Backend (FastAPI)  │
│  ┌──────────────────────────────────────────────────┐   │
│  │              WebSocket Handler (/ws)              │   │
│  │    - Session management                           │   │
│  │    - Audio buffer per session                     │   │
│  │    - Frame manager (rate limit + selection)       │   │
│  └──────┬──────────┬──────────────┬─────────────────┘   │
│         │          │              │                      │
│         ▼          ▼              ▼                      │
│  ┌──────────┐ ┌─────────┐ ┌───────────┐                │
│  │ Whisper  │ │ Frame   │ │ AI Client │                │
│  │ STT      │ │ Mgr     │ │ (abstract)│                │
│  │(faster-  │ │(resize, │ └─────┬─────┘                │
│  │ whisper) │ │ rate-lmt)│      │                       │
│  └────┬─────┘ └────┬────┘      │                       │
│       │ text        │ image     │                       │
│       └─────────────┼───────────┘                       │
│                     ▼                                   │
│              ┌──────────────┐                           │
│              │  AI Provider │                           │
│              │ ┌──────────┐ │                           │
│              │ │ Ollama   │ │ ← HTTP /api/chat          │
│              │ │ (gemma3) │ │   localhost:11434         │
│              │ └──────────┘ │                           │
│              │ ┌──────────┐ │                           │
│              │ │ Gemini   │ │ ← WebSocket (optional)    │
│              │ │ Live API │ │                           │
│              │ └──────────┘ │                           │
│              └──────┬───────┘                           │
│                     │ text response                     │
│                     ▼                                   │
│              ┌──────────┐                               │
│              │   TTS    │                               │
│              │ (Piper / │                               │
│              │  Speech  │                               │
│              │  Synth)  │                               │
│              └──────────┘                               │
└─────────────────────────────────────────────────────────┘
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
5. 后端: whisper_stt.transcribe(audio) → 转写文本
   ↓
6. 后端: frame_manager.get_latest_frame() → 获取最近视频帧
   ↓
7. 后端: ai_client.chat(text=transcript, image=frame) → 流式文本
   ↓
8. 后端: 流式发送 response_text 到前端
   ↓
9. 前端: 更新 ChatLog + SpeechSynthesis.speak(text)
```

### 流程 2：用户打断 AI

```
1. AI 正在生成/播放回复
   ↓
2. 用户开始说话 → VAD 检测 speech_start
   ↓
3. 前端: 停止音频播放
   ↓
4. 前端 → 后端: 发送 interrupt 消息
   ↓
5. 后端: 取消 Ollama 生成 → 清空音频缓冲
   ↓
6. 后端: 开始处理新的用户输入（回到流程 1）
```

### 流程 3：视频帧管理

```
1. 浏览器每 ~200ms 捕获一帧 JPEG（5fps）
   ↓
2. 通过 WebSocket 发送 video_frame 到后端
   ↓
3. frame_manager:
   - 存储最新帧（覆盖旧帧）
   - 缩放至 640x480（如需要）
   - 发送给 AI 时使用最新帧（1fps 有效速率）
```

---

## 会话状态模型

```
Session
  ├── session_id: str (UUID)
  ├── created_at: float
  ├── last_activity: float
  ├── audio_buffer: List[bytes]     # PCM16 音频块
  ├── latest_frame: bytes | None    # 最新 JPEG 帧
  ├── frame_count: int
  ├── is_ai_speaking: bool          # AI 是否在生成中
  └── interrupt_flag: asyncio.Event
```

---

## 组件职责

### 前端组件

| 组件 | 职责 | 依赖 |
|------|------|------|
| App | 根组件，管理全局状态 | 所有 hooks |
| VideoPanel | 摄像头预览 | useMediaStream |
| AudioIndicator | VAD 状态指示 | useVAD |
| ChatLog | 对话记录展示 | WebSocket 消息 |
| ConnectionStatus | WS 连接状态 | useWebSocket |
| ControlBar | 控制面板 | useMediaStream, useWebSocket |

### 后端服务

| 服务 | 职责 |
|------|------|
| ws.py | WebSocket 连接管理、消息路由、会话协调 |
| ollama_client.py | Ollama HTTP API 调用、流式生成 |
| whisper_stt.py | 语音→文本转写 |
| frame_manager.py | 帧缓存、帧率控制、缩放 |
| audio.py | PCM 缓冲管理 |
| tts.py | 文字→语音合成 |
