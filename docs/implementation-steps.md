# AI Visual Conversation Assistant — 实施步骤

> 详细执行计划参见项目计划文件：`C:\Users\Thik Young\.claude\plans\ai-ai-graceful-twilight.md`

---

## 阶段概览

| PR | 分支 | 目标 | 依赖 |
|----|------|------|------|
| 1 | `phase/1-project-setup` | 项目初始化、文档、开发环境 ✅ | 无 |
| 2 | `phase/2-ws-streaming` | 音视频传输管道（无 AI） ✅ | PR 1 |
| 3 | `phase/3-local-ai-core` | Ollama + faster-whisper 核心对话 ✅ | PR 2 |
| 4 | `phase/4-tts-interrupt` | Piper TTS + 用户打断机制 ✅ | PR 3 |
| 5 | `phase/5-polish` | 健壮性、性能优化、测试 ✅ | PR 4 |
| 6 | `phase/6-ui-polish` | 前端 UI 美化：设计系统基础 ✅ | PR 5 |
| 7 | `phase/7-kokoro-tts` | TTS 质量升级：Piper → Kokoro 82M ✅ | PR 4 |

---

## PR 1: 项目初始化与文档框架

### 任务清单

- [x] 创建文件夹结构
- [x] 编写 docs/requirements.md
- [x] 编写 docs/tech-stack.md
- [x] 编写 docs/architecture.md
- [x] 编写 docs/implementation-steps.md
- [x] 创建 dev-logs/INDEX.md（含模板）
- [x] 更新 CLAUDE.md（项目指引）
- [x] 创建 .gitignore
- [x] 创建 .env.example
- [x] 创建 README.md
- [x] 创建 backend/pyproject.toml（uv 项目声明）
- [x] 创建 backend/app/__init__.py + main.py（最小骨架）
- [x] 创建 frontend/package.json
- [x] 创建 frontend 配置（tsconfig.json, vite.config.ts, index.html）
- [x] 创建 frontend/src/main.tsx + App.tsx（空白页）
- [x] 创建 scripts/setup.bat, run-backend.bat, run-frontend.bat
- [x] git init + 首 commit（GitHub 私有仓库已创建）

### 验证标准

- ✅ `scripts/setup.bat` 执行成功
- ✅ `uv run uvicorn app.main:app` 启动无报错，`/health` 返回 200
- ✅ `npm run dev` 打开空白页面，TypeScript 类型检查零错误

---

## PR 2: WebSocket 媒体流骨架

### 任务清单

- [x] 后端：FastAPI + CORS + WebSocket `/ws` 端点
- [x] 后端：PCM 缓冲管理 (audio.py)
- [x] 后端：连接状态管理 (state.py)
- [x] 后端：健康检查路由 (health.py)
- [x] 后端：消息模型定义 (schemas.py)
- [x] 前端：WebSocket 客户端封装 (wsClient.ts)
- [x] 前端：AudioContext 管理 (audioContext.ts)
- [x] 前端：hooks（useWebSocket, useMediaStream, useVAD, useAudioPlayer, useFrameCapture）
- [x] 前端：组件（VideoPanel, AudioIndicator, ConnectionStatus, ControlBar, ChatLog）
- [x] 前端：App 布局 + 样式
- [x] Vite WebSocket 代理配置

### 验证标准

- ✅ 摄像头预览正常（镜像）
- ✅ VAD 检测说话状态（Listening/Speaking）
- ✅ WebSocket 连接成功（Connected 绿灯）
- ✅ 服务器回显音频时长 + 帧计数（状态栏实时更新）

---

## PR 3: 本地 AI 视觉对话核心

### 任务清单

- [x] 后端：OllamaClient（httpx NDJSON 流式 + enable_thinking=False）
- [x] 后端：AudioTranscriber（faster-whisper small, 阈值=disabled, asyncio.to_thread）
- [x] 后端：ConversationOrchestrator（全链路编排：PCM→float32→transcribe→chat→stream）
- [x] 后端：WAV 解析器（手动解析 IEEE_FLOAT format tag 3 → PCM16）
- [x] 后端：config.py（Pydantic Settings 加载 .env）
- [x] 后端：ws.py 集成全链路（video_frame 存帧, speech_end 触发 pipeline, 后台任务管理）
- [x] 后端：schemas.py 扩展（TranscriptPayload, LLMResponsePayload, AIStatusPayload）
- [x] 后端：main.py lifespan 初始化 AI 服务 + /health ollama_available
- [x] 前端：useAudioPlayer（SpeechSynthesis TTS, playAudio/stopPlayback）
- [x] 前端：ChatLog 条件渲染（蓝色用户气泡 / 灰色 AI 气泡流式闪烁 / ai_status / error）
- [x] 前端：消息类型扩展（TranscriptPayload, LLMResponsePayload, AIStatusPayload）
- [x] 前端：App.tsx llm_response delta 累积 + done=true 原地更新气泡 + TTS 触发

### 验证标准

- ✅ Ollama 模型正常响应（qwen3.5:2b-bf16, enable_thinking=False）
- ✅ whisper 正确转写（small 模型, 中文, 阈值 disabled）
- ✅ AI 结合视频内容回答（latest_frame 传图）
- ✅ 浏览器 SpeechSynthesis 朗读回复
- ✅ AI 回复气泡流式显示 + 时间标注

---

## PR 4: TTS 升级 + 打断机制

### 任务清单

- [x] 后端：PiperTTS 服务（asyncio 子进程封装，sentence-level synthesis）
- [x] 后端：split_sentences 工具函数（中英文句边界检测）
- [x] 后端：ConversationOrchestrator 集成 TTS（LLM 流式 → 逐句合成 → tts_audio）
- [x] 后端：打断机制（speech_start → cancel pipeline → send interrupt）
- [x] 后端：schemas 扩展（TTSAudioPayload, InterruptPayload）
- [x] 后端：config + main.py lifespan 初始化（graceful fallback to browser TTS）
- [x] 前端：useAudioPlayer 重写（PCM16 Web Audio API 队列播放 + SpeechSynthesis fallback）
- [x] 前端：App.tsx 集成 TTS 音频 + interrupt 处理 + 本地 barge-in
- [x] 前端：AudioIndicator 新增 AI 说话中状态（蓝色脉冲）
- [x] 前端：ChatLog 处理新消息类型（tts_audio/interrupt 不渲染）
- [x] 脚本：download-piper.ps1（下载 Piper exe + 中英文语音模型）

### 验证标准

- ✅ `npx tsc --noEmit` 零错误
- ✅ `npm run build` 构建成功
- ✅ `uv run python -c "from app.main import app"` 导入成功（v0.3.0）
- ✅ Piper TTS 自然语音输出（huayan-espeak 模型，22050Hz）
- ✅ 用户打断正常工作（本地即时停止 + 服务端任务取消）
- ✅ 无 Piper 时自动回退到浏览器 SpeechSynthesis
- ✅ TTS 文字流式朗读（生产者-消费者队列，LLM 生成中即可开始播放）
- ✅ 双声线问题已修复（tts_info 显式告知前端 TTS 提供方）
- ✅ Markdown 格式字符朗读清洗（**、*、-、` 等）

---

## PR 5: 健壮性与体验优化

### 任务清单

- [x] 后端：WS 心跳 + 会话超时
- [x] 后端：Ollama 健康检查
- [x] 后端：运动检测优化帧率
- [x] 后端：优雅降级错误处理
- [x] 前端：ErrorBoundary
- [x] 前端：重连 + 恢复对话
- [x] 前端：延迟指示器
- [x] 前端：键盘快捷键
- [x] 测试：WS 测试、音频测试
- [x] 压力测试：30 分钟对话

---

## PR 6: 前端 UI 美化：设计系统基础

### 任务清单

- [x] 安装 SKILL：Frontend Design Toolkit + Refactoring UI Plugin
- [x] 创建 CSS 设计 token 体系 (`tokens.css`)
- [x] App.css 全面迁移到 CSS 变量
- [x] 字体统一：六级字号 scale
- [x] 聊天气泡美化：淡入动画、渐变背景、呼吸光标
- [x] 视频面板美化：内阴影、摄像头图标占位符
- [x] 状态栏美化：磨砂玻璃、延迟颜色梯度
- [x] 按钮美化：focus-visible、按下缩放、光晕
- [x] 控制栏美化：磨砂玻璃效果
- [x] 响应式布局：3 断点（768px / 480px / 600px 高度）
- [x] 无障碍增强：aria-label、role、aria-live、prefers-reduced-motion
- [x] 文档更新：dev-logs、INDEX.md、requirements.md、CLAUDE.md
- [x] 新建 docs/design-system.md

### 验证标准

- ✅ `npx tsc --noEmit` 零错误
- ✅ `npm run build` 构建成功
- ✅ `uv run python -c "from app.main import app"` 无报错
- ✅ `uv run pytest tests/ -v` 31/31 全绿
- ✅ 视觉一致：暗色主题、布局不变
- ✅ CSS 变量可通过浏览器 DevTools 修改
- ✅ 所有交互状态正常（hover/active/disabled/focus-visible）
- ✅ 响应式断点自适应（768px / 480px）
- ✅ Tab 键可遍历所有交互元素
- ✅ prefers-reduced-motion 关闭动画
