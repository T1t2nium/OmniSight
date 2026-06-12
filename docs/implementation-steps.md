# AI Visual Conversation Assistant — 实施步骤

> 详细执行计划参见项目计划文件：`C:\Users\Thik Young\.claude\plans\ai-ai-graceful-twilight.md`

---

## 阶段概览

| PR | 分支 | 目标 | 依赖 |
|----|------|------|------|
| 1 | `phase/1-project-setup` | 项目初始化、文档、开发环境 ✅ | 无 |
| 2 | `phase/2-ws-streaming` | 音视频传输管道（无 AI） | PR 1 |
| 3 | `phase/3-local-ai-core` | Ollama + faster-whisper 核心对话 | PR 2 |
| 4 | `phase/4-tts-interrupt` | Piper TTS + 用户打断机制 | PR 3 |
| 5 | `phase/5-polish` | 健壮性、性能优化、测试 | PR 4 |

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

- [ ] 后端：FastAPI + CORS + WebSocket `/ws` 端点
- [ ] 后端：PCM 缓冲管理 (audio.py)
- [ ] 后端：连接状态管理 (state.py)
- [ ] 后端：健康检查路由 (health.py)
- [ ] 后端：消息模型定义 (schemas.py)
- [ ] 前端：WebSocket 客户端封装 (wsClient.ts)
- [ ] 前端：AudioContext 管理 (audioContext.ts)
- [ ] 前端：hooks（useWebSocket, useMediaStream, useVAD, useAudioPlayer）
- [ ] 前端：组件（VideoPanel, AudioIndicator, ConnectionStatus, ControlBar, ChatLog）
- [ ] 前端：App 布局 + 样式
- [ ] Vite WebSocket 代理配置

### 验证标准

- 摄像头预览正常
- VAD 检测说话状态
- WebSocket 连接成功
- 服务器回显音频/帧信息

---

## PR 3: 本地 AI 视觉对话核心

### 任务清单

- [ ] 后端：AIClient 抽象基类
- [ ] 后端：OllamaClient 实现
- [ ] 后端：faster-whisper STT 封装
- [ ] 后端：FrameManager 帧率控制
- [ ] 后端：TTS 抽象（初版：浏览器 SpeechSynthesis）
- [ ] 后端：ws.py 集成全链路
- [ ] 前端：useAudioPlayer 音频播放队列
- [ ] 前端：ChatLog 对话记录展示
- [ ] 前端：消息类型扩展

### 验证标准

- Ollama 模型正常响应
- whisper 正确转写
- AI 能结合视频内容回答
- 浏览器播放语音回复

---

## PR 4: TTS 升级 + 打断机制

### 任务清单

- [ ] 后端：Piper TTS 集成
- [ ] 后端：流式 TTS 输出
- [ ] 后端：打断机制（interrupt flag + 生成取消）
- [ ] 前端：PCM16 音频队列播放
- [ ] 前端：打断触发 + 播放停止
- [ ] 前端：AI 说话中状态指示

### 验证标准

- Piper TTS 自然语音输出
- 用户打断正常工作
- 连续对话流畅

---

## PR 5: 健壮性与体验优化

### 任务清单

- [ ] 后端：WS 心跳 + 会话超时
- [ ] 后端：Ollama 健康检查
- [ ] 后端：运动检测优化帧率
- [ ] 后端：优雅降级错误处理
- [ ] 前端：ErrorBoundary
- [ ] 前端：重连 + 恢复对话
- [ ] 前端：延迟指示器
- [ ] 前端：键盘快捷键
- [ ] 测试：WS 测试、音频测试
- [ ] 压力测试：30 分钟对话
