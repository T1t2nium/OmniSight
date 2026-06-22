# PR 12: 文档解析 + 实体提取服务

**日期**: 2026-06-23
**分支**: `phase/12-document-parser`
**PR**: [#12](https://github.com/T1t2nium/OmniSight/pull/12)
**状态**: ✅ 已完成

---

## 完成事项

### A. 文档解析

| # | 内容 | 文件 |
|---|------|------|
| 1 | `DocumentParser.parse()` — 自动检测格式（PDF/DOCX），返回 ParsedDocument | [document_parser.py](backend/app/services/document_parser.py) |
| 2 | PDF 解析 — pdfplumber 逐页提取文本 | 同上 |
| 3 | DOCX 解析 — python-docx 提取段落 + 表格文本 | 同上 |
| 4 | `UnsupportedFormatError` — 不支持格式抛出明确异常 | 同上 |

### B. 实体提取

| # | 内容 | 文件 |
|---|------|------|
| 1 | `EntityExtractor.extract_jd()` — JD 技能/经验/学历/职责提取 | [entity_extractor.py](backend/app/services/entity_extractor.py) |
| 2 | `EntityExtractor.extract_resume()` — 简历姓名/联系方式/技能/经历/学历提取 | 同上 |
| 3 | `EntityExtractor.match()` — JD-简历匹配，技能缺口 + 百分比 + 经验/学历检查 | 同上 |
| 4 | 技能词表 — 150+ 中英文技能关键词（编程/框架/云/软技能/管理） | 同上 |
| 5 | 经验年限提取 — 支持范围格式 "3-5年" 取低值 | 同上 |
| 6 | 学历关键词匹配 — 博士/硕士/本科/大专四档 | 同上 |
| 7 | 工作经历解析 — 日期段 + 公司/职位识别 | 同上 |
| 8 | JD 职责提取 — 列表项检测（编号/符号/关键词开头） | 同上 |

### C. 数据模型

| # | 内容 | 文件 |
|---|------|------|
| 1 | `ParsedDocument` — 统一文档结构（raw_text, pages, metadata） | [interview.py](backend/app/models/interview.py) |
| 2 | `JDEntities` — JD 实体（技能/经验/学历/职责） | 同上 |
| 3 | `ResumeEntities` — 简历实体（姓名/技能/经历/学历） | 同上 |
| 4 | `WorkExperience` — 工作经历条目 | 同上 |
| 5 | `SkillGap` — 技能缺口 | 同上 |
| 6 | `MatchResult` — 匹配结果（百分比/缺口/建议） | 同上 |

### D. 依赖

| 变更 | 版本 |
|------|------|
| 新增 `pdfplumber` | >=0.11.0 |
| 新增 `python-docx` | >=1.1.0 |
| 新增 `fpdf2` (dev) | — 测试用 PDF 生成 |

### E. Bug 修复

| # | 问题 | 修复 |
|---|------|------|
| 1 | Agent 标签只在对话开始后显示 | `agent_list` 改为 WebSocket connect 时立即发送，不再等首条消息 |

---

## 技术决策

| # | 决策 | 理由 |
|---|------|------|
| 1 | 规则驱动而非 AI | PR 12 专注文档结构解析，词表+正则足够；AI 深度理解留给 PR 13 |
| 2 | pdfplumber 而非 PyMuPDF | 纯 Python，无系统依赖，中文 PDF 文本提取质量好 |
| 3 | python-docx 处理 DOCX | 标准库，段落+表格提取稳定 |
| 4 | 纯同步方法（静态方法） | pdfplumber/python-docx 是同步库，无需 asyncio |
| 5 | 无 WebSocket 集成 | 纯服务层 API，PR 13 InterviewAgent 接入 |

---

## 验证结果

```
57 passed in 0.99s
Frontend TypeScript: zero errors
DocumentParser: PDF + DOCX ✅
EntityExtractor: JD + Resume + Match ✅
技能词表: 150+ 中英文关键词 ✅
agent_list 即时发送修复 ✅
```

---

## 下一步

- [ ] PR 13: InterviewAgent 面试前 — 文档上传 + 动态题库生成
- [ ] PR 14: InterviewAgent 面试中 — 全双工语音 + STAR 追问
- [ ] PR 15: InterviewAgent 面试后 — 结构化评分 + 报告
- [ ] PR 16: 端到端集成测试 + 文档完善
