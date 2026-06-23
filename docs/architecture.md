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

### 流程 5：面试前 — 文档上传 → 题库生成

```
1. 前端: 用户选择企业海面助手
   ↓
2. 前端: DocumentUpload 双区拖拽上传 JD + 简历
   ↓
3. 前端 → 后端: document_upload { doc_type, filename, data: base64 }
   ↓
4. 后端: DocumentParser.parse(bytes, filename) → 提取文本
   ↓
5. 后端: EntityExtractor.extract_jd() / extract_resume() → 结构化实体
   ↓
6. 如果 JD + 简历都已就绪:
   a. EntityExtractor.match(jd, resume) → MatchResult
   b. 后端 → 前端: document_parsed { jd_entities, resume_entities, match_result }
   c. 异步: QuestionGenerator.generate(ai_client, jd, resume, match)
   d. 后端 → 前端: question_bank { categories: [...], total_questions }
```

### 流程 6：面试中 — STAR 追问

```
1. 前端: 用户点击 Start → start_interview
   ↓
2. 后端: _handle_start_interview
   - 验证 question_bank 已就绪
   - build_interview_instructions(question_bank, jd, resume, match)
   - 注入 instructions 到 AI pipeline 的 system_prompt
   - 后端 → 前端: interview_started
   ↓
3. 正常对话流水线（与 ChatAgent 共用）:
   audio_chunk → AudioBuffer → faster-whisper → BailianHTTP(instructions) → TTS
   ↓
4. 对话记录: _save_history 同步写入 interview_transcript
   ↓
5. 前端: 用户点击 Stop → stop_interview
   ↓
6. 后端: _handle_stop_interview
   - 发送 interview_stopped (含 transcript)
   - 异步触发评分 (流程 7)
```

### 流程 7：面试后 — AI 评分 → 报告推送

```
1. _handle_stop_interview 末尾:
   asyncio.create_task(_generate_interview_report(ws, session_id, transcript))
   ↓
2. _generate_interview_report:
   - InterviewScorer.generate_report(ai_client, transcript, jd, resume, match)
   - session.interview_report = report
   - 后端 → 前端: interview_report { scores, overall_score, strengths, weaknesses, recommendation }
   ↓
3. 前端: ReportViewer
   - 加载骨架屏 → 雷达图 + 5 维评分条 + 强弱项 + 录用建议
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
  ├── latest_frame: str | None              # base64 JPEG，每次 video_frame 覆盖
  ├── latest_frame_timestamp: float
  ├── ai_status: str                        # idle | listening | thinking | speaking
  ├── history: list[dict]                   # 多轮对话历史 (PR 8)
  ├── selected_agent: str = "chat"          # 当前会话选中的 Agent (PR 11)
  ├── jd_entities: dict | None              # JD 实体提取结果 (PR 13)
  ├── resume_entities: dict | None          # 简历实体提取结果 (PR 13)
  ├── match_result: dict | None             # JD-简历匹配分析 (PR 13)
  ├── question_bank: dict | None            # AI 生成的结构化题库 (PR 13)
  ├── interview_active: bool = False        # 面试是否进行中 (PR 14)
  ├── interview_instructions: str = ""      # 增强后的面试 system_prompt (PR 14)
  ├── interview_transcript: list[dict]      # 面试对话逐字记录 (PR 14)
  └── interview_report: dict | None         # AI 评分报告 (PR 15)
```

---

## 组件职责

### 前端组件

| 组件 | 职责 | 依赖 |
|------|------|------|
| App | 根组件，管理全局状态 | 所有 hooks |
| AgentSelector | Agent 选择器（下拉菜单） | useAgent |
| VideoPanel | 摄像头预览 | useMediaStream |
| AudioIndicator | VAD + AI 状态指示 | useVAD |
| ChatLog | 对话记录展示 | WebSocket 消息 |
| ConnectionStatus | WS 连接状态 | useWebSocket |
| ControlBar | 控制面板 | useMediaStream, useWebSocket |
| NeuralBackground | Canvas 流场粒子背景 | Canvas API |
| DocumentUpload | 双区拖拽上传（JD + 简历） | WebSocket |
| QuestionBank | 下拉分类题库 | WebSocket 消息 |
| RadarChart | Canvas 五维雷达图 | Canvas API |
| ReportViewer | 可折叠面试报告卡片 | RadarChart + WebSocket |

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
| bailian_ws_client.py | 百炼 Realtime WebSocket 客户端（备用） |
| conversation.py | 全链路编排：STT → Agent → LLM → TTS |
| agents/base.py | BaseAgent ABC + AgentRegistry 单例 + ChatAgent |
| agents/interview/agent.py | InterviewAgent — 企业海面助手 |
| transcriber.py | faster-whisper 语音转写（ModelScope 下载 + CUDA） |
| sherpa_tts.py | sherpa-onnx TTS（默认，中文最佳质量） |
| tts.py | Piper TTS（子进程后备） |
| audio.py | PCM 缓冲管理 |
| frame_manager.py | 帧缓存、帧率控制、运动检测 |
| prompts.py | 多 Agent 共享 System Prompt 管理 |
| document_parser.py | PDF/DOCX 文本提取（pdfplumber + python-docx） |
| entity_extractor.py | JD/简历规则实体提取 + 加权技能匹配 |
| question_generator.py | AI 驱动的分类面试题库生成 |
| interview_engine.py | 面试进行中指令构建（instructions builder） |
| interview_scorer.py | AI 驱动的五维评分 + 决策报告 |
