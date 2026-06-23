# PR 16 — 端到端集成测试 + 文档完善

**日期**: 2026-06-24
**分支**: `phase/16-integration`
**状态**: ✅ 已完成

---

## 目标

- 补充端到端集成测试覆盖面试全流程（start → stop → report）
- 建立前端测试基础设施（vitest + 14 个消息协议测试）
- 全面更新 8 份过期文档 + 新增 Agent 框架开发指南

## 新增文件

| 文件 | 说明 |
|------|------|
| `backend/tests/test_interview_pipeline.py` | 面试全流程集成测试（6 tests） |
| `frontend/src/types/__tests__/messages.test.ts` | WS 消息协议运行时验证（14 tests） |
| `docs/agent-framework.md` | Agent 框架开发指南 — 架构、如何添加新 Agent、UI Config 契约、管线集成 |

## 修改文件

| 文件 | 变更内容 |
|------|----------|
| `backend/tests/conftest.py` | +46 行：共享 MockAIClient 类 + mock_report_json() 辅助函数 |
| `frontend/package.json` | +2 scripts：`test` / `test:watch`，+vitest 4.x devDeps |
| `README.md` | 全面重写 → v0.10.0，加入 Agent/面试特性、百炼配置、开发进度表 PR 10-16 |
| `docs/architecture.md` | +3 数据流（面试前/中/后）、SessionState 模型扩展、服务/组件表扩展 |
| `docs/requirements.md` | +20 条：F12-F16 功能需求（文档解析、实体匹配、题库、面试、评分） |
| `docs/design-system.md` | +5 组件编目：DocumentUpload, QuestionBank, RadarChart, ReportViewer, AgentSelector |
| `docs/tech-stack.md` | +后端服务表、+前端组件表、+WS 消息协议完整列表、+文档/面试依赖 |
| `设计文档.md` | +F10/F12-F16 用户故事映射、+额外交付 6 项、+实现率表、+百炼成本分析 |
| `dev-logs/INDEX.md` | +1 PR 16 条目 |

## 技术决策

### MockAIClient 共享
提权到 `conftest.py` 作为通用测试工具。通过在测试中 `SimpleNamespace(_ai_client=mock)` 注入 `app.state.orchestrator`，绕过 FastAPI lifespan 需求。`_generate_interview_report` 和 `_generate_question_bank` 均通过此路径访问 AI 客户端。

### Interview 全流程测试
由于 `_generate_interview_report` 仅当 `session.interview_transcript` 非空时触发，测试通过 `asyncio.run()` 直接操作 `state_manager` 注入合成 transcript。音频/VAD/STT 管线留待端到端手动测试验证。

### vitest 选型
仅安装 `vitest`（纯 Node 环境），不引入 jsdom/React Testing Library。测试聚焦于 WS 消息协议的运行时结构验证 — 消息信封、Agent 列表、评分报告、题库、文档上传等 14 个场景。TypeScript 类型安全由 `tsc --noEmit` 保证。

### 文档全面检修
PR 10-15 累积了大量新功能但文档未同步。本次 update 覆盖所有 8 份过期文档，新增 `docs/agent-framework.md` 填补「如何添加新 Agent」的知识空白。

## 测试结果

| 套件 | 状态 | 数量 |
|------|------|------|
| `uv run pytest tests/ -v` | ✅ 0 failures | 135 tests |
| `npx tsc --noEmit` | ✅ 0 errors | — |
| `npx vitest run` | ✅ 14 passed | 14 tests |
| `npm run build` | ✅ success | — |

## 下一步

v0.10.0 功能完整。后续方向：
- Electron 桌面应用打包
- 对话历史持久化存储
- 面试 transcript 导出（PDF/Word）
