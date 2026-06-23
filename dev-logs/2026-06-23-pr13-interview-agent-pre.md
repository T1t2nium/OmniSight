# PR 13: InterviewAgent 面试前 — 文档上传 + 动态题库生成

**日期**: 2026-06-23
**分支**: `phase/13-interview-agent-pre`
**PR**: [#13](https://github.com/T1t2nium/OmniSight/pull/13)
**状态**: ✅ 已完成

---

## 完成事项

### A. InterviewAgent

| # | 内容 | 文件 |
|---|------|------|
| 1 | `InterviewAgent` 实现 `BaseAgent` — agent_id="interview"，专属面试官 system prompt | [agent.py](backend/app/agents/interview/agent.py) |
| 2 | `get_ui_config()` — 开启文档上传和题库展示 UI | 同上 |
| 3 | 注册到 `AgentRegistry`（main.py lifespan） | [main.py](backend/app/main.py) |

### B. QuestionGenerator

| # | 内容 | 文件 |
|---|------|------|
| 1 | `QuestionGenerator.generate()` — AI 驱动的分类题库生成 | [question_generator.py](backend/app/services/question_generator.py) |
| 2 | 四类问题：破冰(icebreaker) / 专业技能(technical) / STAR行为(behavioral) / 压力测试(stress) | 同上 |
| 3 | Prompt 包含 JD + 简历 + 匹配分析上下文 | 同上 |
| 4 | 降级兜底：AI 返回无法解析时使用基础问题模板 | 同上 |
| 5 | 解析支持：纯 JSON / ```json fence / 额外文字混杂 | 同上 |

### C. 数据模型

| # | 内容 | 文件 |
|---|------|------|
| 1 | `InterviewQuestion` — id/text/category/difficulty/reference | [interview.py](backend/app/models/interview.py) |
| 2 | `QuestionCategory` — name/type/icon/questions/expanded | 同上 |
| 3 | `QuestionBank` — categories/total_questions/generated_at | 同上 |
| 4 | `QUESTION_CATEGORIES` 常量映射表 | 同上 |

### D. WebSocket 消息

| # | 内容 | 说明 |
|---|------|------|
| 1 | `document_upload` (client→server) | 上传 JD/简历文件 (base64) |
| 2 | `document_parsed` (server→client) | 解析结果 + 匹配分析 |
| 3 | `question_bank` (server→client) | AI 生成的分类题库 |
| 4 | `agent_list` 扩展 | 携带 `ui_config` 供前端条件渲染 |

### E. 前端组件

| # | 内容 | 文件 |
|---|------|------|
| 1 | `DocumentUpload` — 双区拖拽上传（JD + 简历），HTML5 Drag & Drop | [DocumentUpload.tsx](frontend/src/components/DocumentUpload.tsx) |
| 2 | `QuestionBank` — 折叠分类题库，难度徽章 + 技能标签 | [QuestionBank.tsx](frontend/src/components/QuestionBank.tsx) |
| 3 | `useAgent` 扩展 — 暴露 `uiConfig`，Agent 切换时更新 UI 配置 | [useAgent.ts](frontend/src/hooks/useAgent.ts) |

### F. SessionState 扩展

| # | 字段 | 用途 |
|---|------|------|
| 1 | `jd_entities` / `resume_entities` | 解析后的 JD/简历实体 |
| 2 | `match_result` | JD-简历匹配结果 |
| 3 | `question_bank` | 生成的题库缓存 |
| 4 | `jd_filename` / `resume_filename` | 原始文件名 |

### G. UI 配置协议

| 字段 | ChatAgent | InterviewAgent |
|------|-----------|---------------|
| `show_document_upload` | `false` | `true` |
| `show_question_bank` | `false` | `true` |
| `header_color` | `#6366f1` (紫) | `#10b981` (绿) |

### H. UI 迭代优化

| # | 内容 | 文件 |
|---|------|------|
| 1 | AgentSelector 重构为下拉菜单（玻璃态，点击外部自动关闭） | [AgentSelector.tsx](frontend/src/components/AgentSelector.tsx) |
| 2 | DocumentUpload 从视频下方移至视频右侧并排（flex row，左边界对齐视频右边界） | [App.tsx](frontend/src/App.tsx) + [App.css](frontend/src/App.css) |
| 3 | 删除收束/展开/滑动动画逻辑，面板固定不覆盖视频 | 同上 |
| 4 | QuestionBank 修复遮挡聊天框问题（删入场动画，加 flex-shrink:0） | [App.css](frontend/src/App.css) |
| 5 | 响应式：≤768px 时面板自动落到视频下方 | 同上 |

### I. Agent 对话隔离

| # | 内容 | 文件 |
|---|------|------|
| 1 | 新增 `reset_conversation` WS 消息：清空 session.history + interview 状态 | [ws.py](backend/app/routes/ws.py) |
| 2 | `agent_select` 时自动清空 history（Agent 间上下文不共享） | 同上 |
| 3 | 前端 `handleStartConversation` 发 `reset_conversation`（每次会话从零开始） | [App.tsx](frontend/src/App.tsx) |
| 4 | AgentSelector 对话中禁用（`disabled` prop，45% 透明度） | [AgentSelector.tsx](frontend/src/components/AgentSelector.tsx) |
| 5 | 禁用态 CSS：`pointer-events:none`，`cursor:not-allowed` | [App.css](frontend/src/App.css) |
| 6 | 新增 test_reset_conversation_clears_history | [test_ws.py](backend/tests/test_ws.py) |

---

## 技术决策

| # | 决策 | 理由 |
|---|------|------|
| 1 | 题库生成复用已有 AI Client | 不引入新的 AI 依赖，Ollama/Bailian 双引擎 |
| 2 | 降级兜底基础问题 | AI 返回不可解析时不阻塞流程 |
| 3 | 前端条件渲染基于 ui_config | Agent 切换时自动显示/隐藏相关 UI |
| 4 | 文档上传状态由 App 管理 | 保持单一数据源，DocumentUpload 为受控组件 |
| 5 | HTML5 原生 Drag & Drop | 零依赖，符合项目原则 |
| 6 | 题库异步后台生成 | 不阻塞文档解析响应，question_bank 独立推送 |
| 7 | AgentSelector 下拉菜单而非 pills | 紧凑，支持描述文字，更适合多 Agent 扩展 |
| 8 | DocumentUpload 与视频并排（flex row） | 不覆盖视频内容，视觉清晰 |
| 9 | Agent 对话隔离：切换清空 + 对话中锁定 | 防止上下文泄漏，保证每次会话独立 |
| 10 | 前端发 reset_conversation 而非后端自动 | 明确的生命周期控制，避免意外清空 |

---

## 数据流

```
[Agent 切换]  agent_select("interview") → ui_config → 前端显示上传区（同时清空 history）
[开始对话]    前端发送 reset_conversation → 后端清空 session.history + interview 状态
[上传 JD]     document_upload(jd) → DocumentParser → EntityExtractor.extract_jd()
[上传简历]    document_upload(resume) → DocumentParser → EntityExtractor.extract_resume()
[自动匹配]    JD + Resume 就绪 → EntityExtractor.match() → MatchResult
[自动生成]    JD + Resume + Match → QuestionGenerator.generate(AI) → QuestionBank
[推送结果]    Server → document_parsed (含 match) + question_bank (分类题库)
[停止对话]    前端清空本地 chatMessages，AgentSelector 恢复可切换
```

### Agent 隔离机制

```
对话前：Agent 可切换 ✅ → 选择 Agent 时清空 session.history
点击 Start → 发送 reset_conversation → 清空全部上下文 → 开始新媒体流
对话中：AgentSelector disabled 🔒（不可切换，防止上下文泄漏）
点击 Stop → 停止媒体 → AgentSelector 恢复 ✅
```

---

## 验证结果

```
80 passed in 1.08s
Frontend TypeScript: zero errors
InterviewAgent: 注册 + WS 消息 ✅
QuestionGenerator: 11/11 tests (生成/解析/兜底) ✅
DocumentUpload: 双区拖拽 ✅
QuestionBank: 折叠分类 ✅
AgentSelector: 下拉菜单 + 对话中禁用 ✅
Agent 隔离: reset_conversation + agent_select 清空 history ✅
Panel layout: flex row 并排，不覆盖视频 ✅
```

---

## 下一步

- [ ] PR 14: InterviewAgent 面试中 — 全双工语音 + STAR 追问
- [ ] PR 15: InterviewAgent 面试后 — 结构化评分 + 报告
- [ ] PR 16: 端到端集成测试 + 文档完善
