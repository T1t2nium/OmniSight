# PR 11: Agent 框架 + Agent 选择器 UI

**日期**: 2026-06-23
**分支**: `phase/11-agent-framework`
**PR**: [#11](https://github.com/T1t2nium/OmniSight/pull/11)
**状态**: ✅ 已完成

---

## 完成事项

### A. Agent 框架

| # | 内容 | 文件 |
|---|------|------|
| 1 | `BaseAgent` ABC — agent_id, name, description, system_prompt, get_ui_config() | [agents/base.py](backend/app/agents/base.py) |
| 2 | `AgentRegistry` 类方法单例 — register/get/list_agents/default_agent_id | [agents/base.py](backend/app/agents/base.py) |
| 3 | `ChatAgent` — 默认视觉聊天伴侣，使用已有 SYSTEM_PROMPT | [agents/base.py](backend/app/agents/base.py) |
| 4 | `system_prompt` 参数注入 — `BaseAIClient.chat()` 新增可选 system_prompt | [base_ai_client.py](backend/app/services/base_ai_client.py) |
| 5 | OllamaClient / BailianHTTPClient — 接收 system_prompt，无则 fallback 默认 | [ollama_client.py](backend/app/services/ollama_client.py), [bailian_http_client.py](backend/app/services/bailian_http_client.py) |
| 6 | ConversationOrchestrator — process_utterance() 新增 system_prompt 参数 | [conversation.py](backend/app/services/conversation.py) |
| 7 | SessionState — 新增 selected_agent 字段追踪每会话的 Agent | [state.py](backend/app/models/state.py) |

### B. WebSocket 消息

| # | 内容 | 文件 |
|---|------|------|
| 1 | agent_list — 会话注册后发送可用 Agent 列表 | [ws.py](backend/app/routes/ws.py) |
| 2 | agent_select — 客户端选择 Agent，储存在 SessionState | [ws.py](backend/app/routes/ws.py) |
| 3 | AI Pipeline — 根据 session 的 Agent 查找 system_prompt，传入 orchestrator | [ws.py](backend/app/routes/ws.py) |
| 4 | AgentInfo, AgentListPayload, AgentSelectPayload — Pydantic 模型 | [schemas.py](backend/app/models/schemas.py) |

### C. 前端 Agent UI

| # | 内容 | 文件 |
|---|------|------|
| 1 | AgentSelector 组件 — 玻璃态胶囊标签，显示当前选中 Agent | [AgentSelector.tsx](frontend/src/components/AgentSelector.tsx) |
| 2 | useAgent hook — 监听 agent_list，提供 selectAgent 函数 | [useAgent.ts](frontend/src/hooks/useAgent.ts) |
| 3 | App.tsx 集成 — Header 中显示 AgentSelector | [App.tsx](frontend/src/App.tsx) |
| 4 | AgentSelector 玻璃态样式 | [App.css](frontend/src/App.css) |
| 5 | Agent 相关 TypeScript 类型 | [types/index.ts](frontend/src/types/index.ts) |

### D. main.py 初始化

| # | 内容 |
|---|------|
| 1 | lifespan 中 AgentRegistry.register(ChatAgent()) |
| 2 | 日志输出注册数量 |

---

## 技术决策

| # | 决策 | 理由 |
|---|------|------|
| 1 | system_prompt 在 Orchestrator 层注入 | AI Client 不再自己决定 prompt，职责更清晰 |
| 2 | AI Client 保留 fallback 默认 prompt | 向后兼容，单独使用 Client 时不受影响 |
| 3 | AgentRegistry 使用类方法 | 无需依赖注入，代码更简洁 |
| 4 | ChatAgent 内联在 base.py | 目前只有 1 个 Agent，不新建单独文件 |
| 5 | Agent 存储在 SessionState | 每会话独立选择，互不干扰 |
| 6 | 前端用胶囊标签而非下拉 | 当前仅 1 个 Agent，标签更自然 |

---

## 验证结果

```
31 passed in 0.09s
Frontend TypeScript: zero errors
Agent 框架: BaseAgent ABC + AgentRegistry + ChatAgent ✅
WS 消息: agent_list 发送 + agent_select 处理 ✅
前端: AgentSelector 玻璃态胶囊标签 ✅
Ollama 模式完全向后兼容 ✅
```

---

## 下一步

- [ ] PR 12: 文档解析 + 实体提取服务 (PDF/Word)
- [ ] PR 13: InterviewAgent 面试前 — 动态题库生成
- [ ] PR 14: InterviewAgent 面试中 — 全双工语音 + STAR 追问
- [ ] PR 15: InterviewAgent 面试后 — 结构化评分 + 报告
- [ ] PR 16: 端到端集成测试 + 文档完善
