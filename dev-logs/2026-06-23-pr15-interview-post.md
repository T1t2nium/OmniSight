# PR 15 — InterviewAgent 面试后：结构化雷达评分 + AI 决策报告

**日期**：2026-06-23 ~ 2026-06-24
**状态**：✅ 已完成
**分支**：`phase/15-interview-post`

---

## A. 目标

面试停止时自动触发 AI 评分：分析完整 transcript + JD/简历匹配数据，输出 5 维雷达评分、
强弱项分析、录用建议。前端新增雷达图和报告卡片展示。

---

## B. 架构

```
[用户点击 Stop]
    ↓ stop_interview
[_handle_stop_interview] → 发送 interview_stopped → 异步触发评分
    ↓ asyncio.create_task
[_generate_interview_report]
    → InterviewScorer.generate_report(ai_client, transcript, jd, resume, match)
    → AI scoring → parse JSON → InterviewReport
    → session.interview_report + 发送 interview_report 到前端
[前端] reportLoading: skeleton → 淡入 ReportViewer（雷达图 + 评分 + 强弱项 + 建议）
```

---

## C. 新建文件

| 文件 | 说明 |
|------|------|
| `backend/app/services/interview_scorer.py` | AI 评分 + 报告生成器（~250 行） |
| `backend/tests/test_interview_scorer.py` | 评分器单元测试（17 tests） |
| `frontend/src/components/RadarChart.tsx` | Canvas 五边形雷达图（零依赖） |
| `frontend/src/components/ReportViewer.tsx` | 报告卡片组件（雷达图 + 评分条 + 强弱项 + 录用建议） |
| `dev-logs/2026-06-23-pr15-interview-post.md` | 本文档 |

---

## D. 修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/models/interview.py` | +2 模型：InterviewScores, InterviewReport |
| `backend/app/models/schemas.py` | +1 Payload：InterviewReportPayload |
| `backend/app/models/state.py` | +1 字段：interview_report |
| `backend/app/routes/ws.py` | `_handle_stop_interview` 触发 `_generate_interview_report` |
| `backend/app/main.py` | version → 0.10.0 |
| `backend/app/services/entity_extractor.py` | 模糊技能匹配 + 别名映射 + 摘要提取 + 短技能词边界修复 |
| `backend/app/services/question_generator.py` | 题库 prompt 增加工作经历详情 + 候选人参测 |
| `frontend/src/types/index.ts` | +2 接口（InterviewScoresPayload + InterviewReportPayload） |
| `frontend/src/App.tsx` | interview_report 处理 + reportLoading 骨架态 + ReportViewer 渲染 |
| `frontend/src/App.css` | 报告卡片 + 骨架屏 + 雷达图 + 全局滚动条统一 |
| `frontend/src/components/ControlBar.tsx` | startDisabled + startHint props |
| `frontend/src/components/QuestionBank.tsx` | 重构为下拉菜单（胶囊按钮 + 绝对定位 popover） |
| `frontend/vite.config.ts` | Vite 插件静默 WS proxy ECONNABORTED 错误 |
| `CLAUDE.md` / `dev-logs` / `docs` | 文档更新 |

---

## E. 数据模型

### InterviewScores（5 维评分 0-100）
- **technical**：技术能力
- **experience**：项目经验
- **communication**：沟通表达
- **role_fit**：岗位匹配
- **stress**：抗压/应变

### InterviewReport
- scores + overall_score
- strengths / weaknesses（各 2-5 条）
- summary + recommendation（强烈推荐/推荐/保留意见/不推荐）

---

## F. 前端交互优化（本轮附赠）

| 优化项 | 说明 |
|--------|------|
| QuestionBank 下拉菜单 | 胶囊按钮 + abs 定位 popover，不推布局 |
| Start 按钮禁用提示 | 琥珀色 contextual hint 逐步引导（请上传 JD → 请上传简历 → 生成题库中...） |
| ReportViewer 加载骨架 | 停止面试后立即显示 "AI 正在生成报告..." + 旋转 spinner + 脉冲骨架条 |
| ReportViewer 折叠 | 默认收拢为一行，点击展开详细报告 |
| 全局滚动条统一 | 5px 半透明细滚动条，所有可滚动区域统一 |
| Vite WS proxy 错误静默 | 前端启动时不再刷红屏 ECONNABORTED |
| 实体提取优化 | 模糊技能匹配 + 60+ 别名映射 + 简历摘要提取 + 工作经历入题库 prompt |
| 短技能词边界修复 | `\br\b` 不再把 Redis 误匹配为 R 语言 |

---

## G. 降级策略

AI 评分 JSON 解析失败 → `_build_fallback_report(match_result)` 基于匹配度估算报告

---

## H. 验证结果

| 验证项 | 结果 |
|--------|------|
| `uv run pytest tests/ -v` | ✅ 129/129 通过（+17 new） |
| `npx tsc --noEmit` | ✅ 零类型错误 |
| 现有 112 测试零回归 | ✅ |

---

## I. 下一步

**PR 16**：端到端集成测试 + 文档完善
