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
| 7 | `phase/7-kokoro-tts` | TTS 质量升级：Piper → sherpa-onnx ✅ | PR 4 |
| 8 | `phase/8-system-prompt` | 系统提示词 + 沉浸式对话体验 ✅ | PR 7 |
| 9 | `phase/9-frontend-ui-final` | 前端 UI 终极优化：Canvas 背景 + 玻璃按钮 ✅ | PR 8 |
| 10 | `phase/10-ai-provider-abstraction` | AI Provider 抽象层 + 百炼 HTTP 集成 ✅ | PR 9 |
| 11 | `phase/11-agent-framework` | Agent 框架 + Agent 选择器 UI ✅ | PR 10 |
| 12 | `phase/12-document-parser` | 文档解析 + 实体提取服务 ✅ | PR 11 |
| 13 | `phase/13-interview-agent-pre` | InterviewAgent 面试前 + 题库生成 ✅ | PR 12 |
| 14 | `phase/14-interview-during` | InterviewAgent 面试中 — 全双工语音 + STAR ✅ | PR 13 |
| 15 | `phase/15-interview-post` | InterviewAgent 面试后 — 评分 + 报告 | PR 14 |
| 16 | `phase/16-integration` | 端到端集成测试 + 文档完善 | PR 15 |

---

## PR 10: AI Provider 抽象层 + 百炼 HTTP 集成

### 任务清单

- [x] 新建 `base_ai_client.py` — BaseAIClient ABC (chat/check_health/close)
- [x] 新建 `bailian_http_client.py` — 百炼 DashScope 多模态生成 HTTP SSE 流式
- [x] 重构 `ollama_client.py` — 实现 BaseAIClient 接口
- [x] 重构 `conversation.py` — OllamaClient → BaseAIClient，完全 provider 无关
- [x] 修改 `config.py` — ai_provider: "ollama" | "bailian"
- [x] 修改 `main.py` — 根据 ai_provider 自动选择初始化客户端
- [x] Whisper 模型下载优化 — ModelScope 国内满速 + CUDA 支持
- [x] sherpa-onnx ORT DLL 版本修复 (1.17 → 1.20+)
- [x] 前端修复 — 一次性 LLM 回复不显示 bug

### 验证标准

- ✅ 31/31 测试全部通过
- ✅ Ollama 模式完全向后兼容
- ✅ 百炼 API Key 配置后 health: ai_provider=bailian, ai_available=true

---

## PR 11: Agent 框架 + Agent 选择器 UI

### 任务清单

- [x] 新建 `agents/base.py` — BaseAgent ABC + AgentRegistry + ChatAgent
- [x] `chat()` 新增 `system_prompt` 参数 (base_ai_client → ollama/bailian)
- [x] `process_utterance()` 透传 system_prompt (conversation.py)
- [x] SessionState 新增 `selected_agent` 字段 (state.py)
- [x] 新增 AgentInfo/AgentListPayload/AgentSelectPayload (schemas.py)
- [x] WS 消息：agent_list (会话注册后发送) + agent_select 处理 (ws.py)
- [x] Agent 管线注入 — session.agent_id → AgentRegistry → system_prompt (ws.py)
- [x] main.py lifespan 中注册 ChatAgent
- [x] 前端 AgentSelector 组件 (玻璃态胶囊标签)
- [x] 前端 useAgent hook (监听 agent_list, 提供 selectAgent)
- [x] 前端类型扩展 (AgentInfo, AgentListPayload, AgentSelectPayload)
- [x] App.tsx 集成 AgentSelector + useAgent

### 验证标准

- ✅ 31/31 测试全部通过
- ✅ TypeScript 零类型错误
- ✅ Header 显示「💬 视觉聊天伴侣」胶囊标签
- ✅ 对话功能正常（system prompt 通过 Agent 框架注入）

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

---

## PR 7: TTS 质量升级 — Piper → sherpa-onnx

### 任务清单

- [x] 调研：诊断 espeak-ng 中文 G2P 根因（拼音→IPA 音节映射缺失）
- [x] 替换引擎：Kokoro → sherpa-onnx（内置 FST + 词典，无运行时 espeak-ng）
- [x] 新建 `sherpa_tts.py`：OfflineTts 封装（VITS/Matcha 模型自动检测）
- [x] 修复 ORT DLL 版本不匹配（`_fix_onnxruntime_dll()` 自动替换）
- [x] 模型下载脚本 `download-sherpa-tts.ps1`（vits-melo-tts-zh_en，163MB）
- [x] 配置更新：`sherpa_model_dir`、`sherpa_speed`、`sherpa_num_threads`
- [x] 三级降级链：sherpa → piper → browser
- [x] PCM16 音频峰值归一化（85% target）
- [x] 前端类型适配（TTSInfoPayload.provider: 'sherpa'）

### 验证标准

- ✅ `npx tsc --noEmit` 零错误
- ✅ `npm run build` 构建成功
- ✅ 31/31 后端测试全绿
- ✅ 中文语音清晰可懂，无口齿不清
- ✅ 短句合成延迟 <300ms
- ✅ Piper 后备引擎可正常切换

---

## PR 8: 系统提示词 + 沉浸式对话体验

### 任务清单

- [x] 新建 `prompts.py` — 集中管理系统提示词
- [x] ollama_client 注入系统提示词 + 历史裁剪（最近 8 条消息）
- [x] SessionState 添加 `history` 字段持久化多轮对话
- [x] conversation.py 返回更新后的对话历史
- [x] ws.py 线程安全的历史保存（`call_soon_threadsafe`）
- [x] 视觉问题检测 `_is_visual_question()`（后续禁用）
- [x] 阿拉伯数字 → 中文转换（≤5 位，TTS 更清晰）
- [x] TTS 文本过滤：Unicode 区块白名单 + Markdown 清洗
- [x] 用户自定义系统提示词（视觉聊天伴侣 v2.1）

### 验证标准

- ✅ AI 回复不再出现"图片/上传/画面中"等割裂表述
- ✅ 连续对话时 AI 能记住上文（多轮历史生效）
- ✅ 无 emoji / Markdown 格式泄漏到 TTS
- ✅ 31/31 后端测试全绿

---

## PR 9: 前端 UI 终极优化 — Canvas 背景 + 玻璃按钮

### 任务清单

- [x] 新建 `NeuralBackground.tsx`：Canvas 流场粒子背景
  - 600 个粒子沿 cos/sin 角度场运动
  - 鼠标排斥交互（150px 半径）
  - 拖尾覆层颜色读取 `--color-bg-primary` CSS 变量
  - Retina 支持 + `prefers-reduced-motion` 回退
  - 颜色随对话状态切换（idle/用户说话/AI 回复）
- [x] 删除 `BackgroundAmbiance.tsx` + 呼吸灯 CSS（~170 行）
- [x] 新建 `GlassButton.tsx`：磨砂玻璃按钮组件
  - 3 种 Variant：primary(绿) / danger(红) / default(中性)
  - Active 切换态
  - backdrop-filter blur + 渐变边缘光环
- [x] ControlBar 3 个 `<button>` → 3 个 `<GlassButton>`
- [x] 新增 11 个 `--color-glass-*` 设计令牌
- [x] 响应式断点适配（768px / 480px）
- [x] 视觉关键词过滤修复：新增动作动词（做/干/举/挥/指/动）
- [x] TTS 括号表情过滤：（微笑）（点头）等
- [x] 禁用视觉关键词过滤，改由用户提示词控制

### 验证标准

- ✅ `npx tsc --noEmit` 零错误
- ✅ `npm run build` 构建成功
- ✅ 31/31 后端测试全绿
- ✅ Canvas 粒子背景流畅运行（零新增依赖）
- ✅ 鼠标移动粒子排斥交互正常
- ✅ 玻璃按钮磨砂效果 + 状态颜色切换正常
- ✅ `prefers-reduced-motion` 动画停止

---

## PR 10: AI Provider 抽象层 + 阿里云百炼 HTTP 集成

### 任务清单

- [x] 后端：`BaseAIClient` ABC 抽象 `chat()` / `check_health()` / `close()`
- [x] 后端：`BailianHTTPClient` 实现（httpx NDJSON 流式，请求签名认证）
- [x] 后端：`OllamaClient` 重构实现 BaseAIClient
- [x] 后端：`chat()` 添加可选的 `system_prompt` 参数
- [x] 后端：`conversation.py` 转发 `system_prompt` 到 AI Client
- [x] 后端：`main.py` `ai_provider` 配置切换 + health 端点扩展
- [x] 后端：`config.py` 百炼 API Key / workspace / model 配置
- [x] 后端：单 chunk 完整 LLM 响应渲染修复（Bailian 不流式）
- [x] 后端：原始 JSON Lines 解析（非 SSE `data:` 前缀）
- [x] 文档：CLAUDE.md 更新

### 验证标准

- ✅ `uv run pytest tests/` 31/31 全绿
- ✅ Ollama → Bailian 切换正常，`AI_PROVIDER=bailian` 生效
- ✅ Bailian 模型返回中文响应

---

## PR 11: Agent 框架 + Agent 选择器 UI

### 任务清单

- [x] 后端：`BaseAgent` ABC — `agent_id` / `name` / `description` / `system_prompt` / `get_ui_config()`
- [x] 后端：`AgentRegistry` — 类方法单例 `register()` / `get()` / `list_agents()`
- [x] 后端：`ChatAgent` — 默认「视觉聊天伴侣」
- [x] 后端：`ws.py` `agent_list` 即时推送（WebSocket connect）+ `agent_select` 处理
- [x] 后端：`session.selected_agent` → `AgentRegistry.get()` → `orchestrator.process_utterance(system_prompt=...)`
- [x] 后端：`schemas.py` AgentInfo / AgentListPayload / AgentSelectPayload
- [x] 后端：`main.py` 注册 ChatAgent
- [x] 前端：`useAgent` hook — 监听 agent_list + selectAgent()
- [x] 前端：`AgentSelector` — 玻璃态胶囊标签（单选/多选）
- [x] 前端：`App.tsx` 集成 AgentSelector

### 验证标准

- ✅ 37/37 后端测试全绿
- ✅ `npx tsc --noEmit` 零错误
- ✅ Agent 标签在 WebSocket 连接后立即显示（无需开始对话）
- ✅ Agent 切换时 system_prompt 正确注入 AI pipeline

---

## PR 12: 文档解析 + 实体提取服务

### 任务清单

- [x] 后端：`DocumentParser` — PDF(pdfplumber) + DOCX(python-docx) 文本提取
- [x] 后端：`EntityExtractor` — 规则驱动 JD/简历实体提取（150+ 技能词表）
- [x] 后端：`EntityExtractor.match()` — 加权技能匹配（required ×1.5, preferred ×0.5）
- [x] 后端：`interview.py` 数据模型（ParsedDocument / JDEntities / ResumeEntities / MatchResult 等）
- [x] 后端：依赖更新 pdfplumber / python-docx / fpdf2(dev)
- [x] 修复：agent_list 提前到 WebSocket connect 时发送

### 验证标准

- ✅ 57/57 后端测试全绿
- ✅ PDF + DOCX 解析正确，中文文本提取正常
- ✅ JD 技能/经验/学历/职责提取准确
- ✅ 简历姓名/联系方式/技能/经历/学历提取准确
- ✅ 匹配百分比 + 技能缺口分析正确

---

## PR 13: InterviewAgent 面试前 — 文档上传 + 动态题库生成

### 任务清单

- [x] 后端：`InterviewAgent` — 实现 BaseAgent（agent_id="interview"，面试官 system prompt）
- [x] 后端：`QuestionGenerator` — AI 驱动的四类题库生成（破冰/技术/STAR/压力）
- [x] 后端：`QuestionBank` 数据模型 — InterviewQuestion / QuestionCategory / QuestionBank
- [x] 后端：`ws.py` document_upload 消息处理 + 完整 pipeline（解析→提取→匹配→题库生成）
- [x] 后端：`agent_list` 扩展 ui_config 字段
- [x] 后端：`SessionState` 扩展 interview 字段（jd_entities / resume_entities / match_result / question_bank）
- [x] 后端：`main.py` 注册 InterviewAgent
- [x] 前端：`DocumentUpload` — 双区拖拽上传（JD + 简历），HTML5 Drag & Drop
- [x] 前端：`QuestionBank` — 折叠分类题库（难度徽章 + 技能标签）
- [x] 前端：`useAgent` 扩展 — 暴露 `uiConfig` 用于条件渲染
- [x] 前端：`App.tsx` 条件渲染 DocumentUpload + QuestionBank
- [x] 前端：`App.css` 玻璃态样式（upload zones + question cards）
- [x] 前端：AgentSelector 重构为下拉菜单（玻璃态，对话中禁用锁定）
- [x] 前端：DocumentUpload 并排布局（flex row，面板左边界对齐视频右边界，不覆盖）
- [x] 前端：QuestionBank 修复遮挡聊天框（删入场动画，加 flex-shrink:0）
- [x] 前端：`handleStartConversation` 发送 `reset_conversation` 清空后端历史
- [x] 后端：`agent_select` 自动清空 `session.history`（Agent 上下文隔离）
- [x] 后端：`reset_conversation` WS 消息处理（清空 history + interview 状态）
- [x] 测试：11+11+1=23 新增测试（agent + question generator + reset_conversation）

### 验证标准

- ✅ 80/80 测试全绿
- ✅ `npx tsc --noEmit` 零错误
- ✅ InterviewAgent 注册成功，agent_list 含 2 个 agent（chat + interview）
- ✅ document_upload → document_parsed → question_bank 端到端流程
- ✅ 题库 AI 解析失败时降级兜底
- ✅ 前端 Agent 切换时 DocumentUpload/QuestionBank 自动显示/隐藏
- ✅ Agent 对话隔离：切换 Agent 清空 history，对话中禁止切换
- ✅ 每次 Start → 新上下文，Stop → AgentSelector 恢复可切换
- ✅ 面板不覆盖视频（flex row 并排），不遮挡聊天框

---

## PR 14: InterviewAgent 面试中 — 全双工语音 + STAR 追问

### 任务清单

- [x] 后端：`BailianWSClient` — 百炼 OmniRealtime WebSocket 客户端（全双工音频）
- [x] 后端：`DuringInterviewEngine` — 面试进行中引擎（指令构建 + 事件中继）
- [x] 后端：`ws.py` start/stop_interview handler + 面试事件循环 + audio/vad 路由
- [x] 后端：`schemas.py` +2 Payload（InterviewStartedPayload / InterviewStoppedPayload）
- [x] 后端：`SessionState` +3 字段（interview_active / interview_engine / interview_transcript）
- [x] 后端：`pyproject.toml` 添加 `websockets>=14,<15` 依赖
- [x] 后端：`main.py` version → 0.9.0
- [x] 前端：types 扩展（InterviewStartedPayload / InterviewStoppedPayload）
- [x] 前端：App.tsx 面试 start/stop 集成 + 阶段指示器
- [x] 前端：App.css 面试 UI 样式（header 变体 + 阶段指示器动画）
- [x] 测试：36 新增测试（BailianWSClient 11 + DuringInterviewEngine 25）

### 验证标准

- ✅ 116/116 测试全绿（+36 new）
- ✅ `npx tsc --noEmit` 零类型错误
- ✅ 现有 80 测试零回归
- ✅ 降级路径：API Key 为空时返回友好错误
