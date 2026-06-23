# PR 14 — InterviewAgent 面试中：增强指令 + STAR 追问

**日期**：2026-06-23
**状态**：✅ 已完成
**分支**：`phase/14-interview-during`

---

## A. 目标

实现 InterviewAgent 的"面试中"阶段：复用现有 AI 流水线（faster-whisper + BailianHTTP + Piper TTS），
通过动态构建增强 system_prompt（注入题库 + JD + 简历 + 技能缺口 + STAR 追问规则），
让 AI 按结构化面试流程精准提问。

---

## B. 架构

**最终方案**：不替换本地 TTS/STT，不引入百炼 Realtime WS。

```
InterviewAgent 面试中（与 ChatAgent 共用流水线）:
audio_chunk → AudioBuffer → faster-whisper → BailianHTTP（增强 instruction）→ Piper TTS
                                                      ↑
                                          build_interview_instructions()
                                          (题库+JD+简历+STAR规则)
```

- `interview_engine.py` 是纯 utility，负责构建 instruction 字符串
- `ws.py` 在 interview_active 时将 instruction 注入 `_start_ai_pipeline` 的 `system_prompt`
- `_save_history` 自动累积 `interview_transcript` 供 PR 15 评分使用

---

## C. 新建文件

| 文件 | 说明 |
|------|------|
| `backend/app/services/bailian_ws_client.py` | 百炼 Realtime WS 客户端（备用，当前流程未使用） |
| `backend/app/services/interview_engine.py` | `build_interview_instructions()` — 指令构建器 |
| `backend/tests/test_bailian_ws_client.py` | BailianWSClient 单元测试 (11 tests) |
| `backend/tests/test_interview_engine.py` | 指令构建器测试 (22 tests) |
| `dev-logs/2026-06-23-pr14-interview-during.md` | 本文档 |

---

## D. 修改文件

| 文件 | 变更详情 |
|------|---------|
| `backend/pyproject.toml` | + `websockets>=14,<15`（BailianWSClient 依赖，备用） |
| `backend/app/main.py` | version → 0.9.0 |
| `backend/app/routes/ws.py` | +~100 行：start/stop_interview handler；`_start_ai_pipeline` 注入 interview_instructions；`_save_history` 累积 transcript |
| `backend/app/models/schemas.py` | +2 Payload：InterviewStartedPayload / InterviewStoppedPayload |
| `backend/app/models/state.py` | +3 字段：interview_active / interview_instructions / interview_transcript |
| `frontend/src/types/index.ts` | +2 TS 接口 |
| `frontend/src/App.tsx` | ~40 行：面试 start/stop 集成 + `🎙️ 面试中` 标签 |
| `frontend/src/App.css` | ~30 行：面试 header 绿色变体 + 标签动画 |
| `CLAUDE.md` | +2 关键路径 |
| `dev-logs/INDEX.md` | +1 日志索引 |
| `docs/implementation-steps.md` | +PR 14 任务清单 |

---

## E. 数据流

```
[用户选择 InterviewAgent → 上传 JD+简历 → 题库生成]
    ↓ 点击「开始对话」
[Frontend] start_interview → Backend
    ↓ build_interview_instructions(bank, jd, resume, match)
    ↓ 存入 session.interview_instructions
[Backend → Frontend] interview_started → header 变绿 + "🎙️ 面试中" 标签
    ↓ 正常 VAD + 语音流程...
[User 说话] → audio_chunk → faster-whisper → BailianHTTP(system_prompt=instructions)
    ↓ 流式返回 + Piper TTS → 前端播放
[_save_history] → 自动同步 interview_transcript
    ↓ 点击「停止」
[Frontend] stop_interview → Backend
[Backend → Frontend] interview_stopped（含 transcript 条目数）
```

---

## F. 验证结果

| 验证项 | 结果 |
|--------|------|
| `uv run pytest tests/ -v` | ✅ 112/112 通过（+32 new） |
| `npx tsc --noEmit` | ✅ 零类型错误 |
| 现有测试零回归 | ✅ |
| 本地 TTS/STT 不受影响 | ✅ 全程复用现有流水线 |
| 题库未就绪防护 | ✅ 前端 alert 提示等待 |

---

## G. 过程中踩坑与修正

1. **websockets 14.x API 不兼容**：`extra_headers` → `additional_headers`，`websockets.asyncio.connect` → `websockets.connect`
2. **百炼 Realtime API 模型/音色不支持**：`qwen3.5-omni-plus-2026-03-15` 不兼容 Realtime 端点，Cherry 音色不可用 → 最终放弃 Realtime WS，改用现有 HTTP 流水线
3. **阶段指示器不可靠**：AI 内部推进阶段但无结构化信号 → 改为静态 `🎙️ 面试中` 标签

---

## H. 下一步

**PR 15**: InterviewAgent 面试后 — 结构化雷达打分 + 报告生成
- InterviewScorer（基于 transcript 评分）
- ReportGenerator（综合报告）
- RadarChart（前端 Canvas 雷达图）
