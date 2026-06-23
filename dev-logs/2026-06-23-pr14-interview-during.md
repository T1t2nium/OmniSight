# PR 14 — InterviewAgent 面试中：全双工语音 + STAR 追问

**日期**：2026-06-23
**状态**：✅ 已完成
**分支**：`phase/14-interview-during`

---

## A. 目标

实现 InterviewAgent 的"面试中"阶段：通过百炼实时 WebSocket API 驱动全双工语音对话，AI 基于题库逐轮提问，应用 STAR 法则深度追问，支持语义打断。

---

## B. 架构决策

**两种流水线共存**：
- **ChatAgent (保持不变)**：`faster-whisper → BailianHTTP → Piper TTS`
- **InterviewAgent (新增)**：`BailianWSClient → Bailian Realtime WS (内部 ASR+LLM+TTS)`

实时模式绕过本地 transcriber + TTS，直接利用百炼 Realtime 全双工能力。降级策略：API Key 为空时回退到原 HTTP 流水线。

**BailianWSClient 不实现 BaseAIClient**：两个协议接口完全不同 — 实时 API 是音频输入/输出，chat() 是文本输入 → 文本增量输出。

---

## C. 新建文件

| 文件 | 说明 | 行数 |
|------|------|------|
| `backend/app/services/bailian_ws_client.py` | 百炼 Realtime WS 客户端 | ~280 |
| `backend/app/services/interview_engine.py` | 面试进行中引擎 | ~280 |
| `backend/tests/test_bailian_ws_client.py` | BailianWSClient 单元测试 (11 tests) | ~110 |
| `backend/tests/test_interview_engine.py` | DuringInterviewEngine 单元测试 (25 tests) | ~370 |
| `dev-logs/2026-06-23-pr14-interview-during.md` | 本文档 | — |

---

## D. 修改文件

| 文件 | 变更详情 |
|------|---------|
| `backend/pyproject.toml` | + `websockets>=14,<15` |
| `backend/app/main.py` | version → 0.9.0 |
| `backend/app/routes/ws.py` | +~200 行：interview handler、事件循环、audio/vad 路由、清理 |
| `backend/app/models/schemas.py` | +2 Payload: InterviewStartedPayload, InterviewStoppedPayload |
| `backend/app/models/state.py` | +3 字段: interview_active, interview_engine, interview_transcript |
| `frontend/src/types/index.ts` | +2 TS 接口 |
| `frontend/src/App.tsx` | ~50 行：面试 start/stop 集成 + 阶段指示器 |
| `frontend/src/App.css` | ~30 行：面试 header 变体 + 阶段指示器样式 |
| `CLAUDE.md` | +2 关键路径 |
| `dev-logs/INDEX.md` | +1 日志索引 |

---

## E. 数据流

```
[用户选择 InterviewAgent → 上传 JD+简历 → 题库生成]
    ↓ 点击「开始面试」
[Frontend] start_interview message → Backend
    ↓ _handle_start_interview
创建 BailianWSClient → 连接 Bailian Realtime WS
创建 DuringInterviewEngine → build_instructions (题库+JD+简历)
    ↓ session.update (instructions)
[Backend → Frontend] interview_started (phase=icebreaker)
    ↓ 面试进行中...
[Frontend] audio_chunk → Backend relay → BailianWSClient → Bailian Realtime
    ↓ server_vad + ASR + LLM + TTS
[Bailian Realtime] events → Backend _interview_event_loop → Frontend
    ↓
[Frontend] 点击「停止面试」
    ↓ stop_interview message
[_handle_stop_interview] 取消事件循环 → 关闭 WS → 保存 transcript
[Backend → Frontend] interview_stopped (含完整 transcript)
```

---

## F. 事件中继映射

| 来自 Bailian Realtime | 发给前端 | 说明 |
|---|---|---|
| `response.audio_transcript.delta` | `llm_response` | AI 增量文本 |
| `response.audio.delta` | `tts_audio` (24kHz) | AI 增量音频 |
| `response.audio_transcript.done` | `llm_response` (done=true) | AI 完整文本 |
| `conversation.item.input_audio_transcription.completed` | `transcript` | 用户语音识别 |
| `input_audio_buffer.speech_started` | `ai_status` (listening) | 用户开始说话 |
| `input_audio_buffer.speech_stopped` | `ai_status` (thinking) | 用户停止说话 |
| `response.done` | `ai_status` (idle) | AI 回复完成 |
| `error` | `error` | 异常 |

---

## G. 验证结果

| 验证项 | 结果 |
|--------|------|
| `uv run pytest tests/ -v` | ✅ 116/116 通过 (+36 new) |
| `npx tsc --noEmit` | ✅ 零类型错误 |
| 现有测试零回归 | ✅ |
| 降级路径 | ✅ API Key 为空时 clear error |

---

## H. 注意事项

- 百炼 Realtime WS 输出 24kHz 音频（输入 16kHz），前端 tts_audio handler 已适配多采样率
- instructions 截断至 ~2KB（题库过大时保留前 15 题 + 摘要）
- 百炼 Realtime WS 会话上限 120 分钟，面试场景足够
- `websockets` 纯 Python 库，无 C 扩展，跨平台兼容
- 降级模式：`BAILIAN_API_KEY` 为空时返回友好错误

---

## I. 下一步

**PR 15**: InterviewAgent 面试后 — 结构化雷达打分 + 报告生成
- InterviewScorer (基于 transcript + JD 匹配度打分)
- ReportGenerator (综合报告 + 录用建议)
- RadarChart (前端 Canvas 雷达图)
- ReportViewer (报告展示组件)
