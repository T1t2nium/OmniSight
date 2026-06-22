# PR 10: AI Provider 抽象层 + 阿里云百炼 HTTP 集成

**日期**: 2026-06-22
**分支**: `phase/10-ai-provider-abstraction`
**PR**: [#10](https://github.com/T1t2nium/OmniSight/pull/10)
**状态**: ✅ 已完成

---

## 完成事项

### A. AI Provider 抽象层

| # | 内容 | 文件 |
|---|------|------|
| 1 | `BaseAIClient` ABC — `chat()`, `check_health()`, `close()`, `model`, `provider_name` | [base_ai_client.py](backend/app/services/base_ai_client.py) |
| 2 | `OllamaClient` 重构 — 继承 `BaseAIClient`，内部逻辑不变 | [ollama_client.py](backend/app/services/ollama_client.py) |
| 3 | `BailianHTTPClient` — 百炼多模态生成 API，原始 JSON 行解析（非 SSE data: 格式） | [bailian_http_client.py](backend/app/services/bailian_http_client.py) |
| 4 | `ai_provider` 新增 `"bailian"`，新增 `bailian_api_key` / `bailian_model` | [config.py](backend/app/config.py) |
| 5 | `ConversationOrchestrator` 接受 `BaseAIClient`（Provider 无关） | [conversation.py](backend/app/services/conversation.py) |
| 6 | `main.py` lifespan — 根据 `ai_provider` 自动选择客户端，Health 端点返回 `ai_provider` + `ai_available` | [main.py](backend/app/main.py) |

### B. Whisper 模型下载优化

| # | 内容 | 文件 |
|---|------|------|
| 1 | CUDA GPU 加速支持 — `whisper_device` 配置项 | [config.py](backend/app/config.py), [transcriber.py](backend/app/services/transcriber.py) |
| 2 | ModelScope（魔搭）国内满速下载，HuggingFace 自动 fallback | [transcriber.py](backend/app/services/transcriber.py) |
| 3 | 懒加载：模型在首次语音输入时才下载，启动秒开 | [transcriber.py](backend/app/services/transcriber.py) |
| 4 | 下载在后台线程运行，Ctrl+C 随时可用 | [transcriber.py](backend/app/services/transcriber.py) |

### C. sherpa-onnx ORT 版本修复

| # | 内容 |
|---|------|
| 1 | 升级 sherpa-onnx 1.13.2 → 1.13.3 |
| 2 | 修复 `_fix_onnxruntime_dll()` 在升级/重装场景下的失效问题（bundled DLL 已被备份为 .bak，旧逻辑直接 return） |
| 3 | 新增场景处理：bundled DLL 缺失时直接复制系统 ORT DLL |

### D. 前端 Bug 修复

| # | 内容 | 文件 |
|---|------|------|
| 1 | 一次性返回的 LLM 回复（无流式增量）在聊天框不显示 — `llmBufferRef` 为空时 fallback 到 `p.delta` | [App.tsx](frontend/src/App.tsx) |

### E. 依赖更新

| 变更 | 版本 |
|------|------|
| 新增 `modelscope` | >=1.23 (ModelScope 魔搭模型下载) |
| 升级 `sherpa-onnx` | 1.13.2 → 1.13.3 |

---

## 技术决策

| # | 决策 | 理由 |
|---|------|------|
| 1 | 不用 dashscope SDK，直接 httpx 调用 | 与项目已有模式一致，无额外依赖 |
| 2 | Whisper 模型从 ModelScope 下载 | 国内满速，HuggingFace 自动 fallback |
| 3 | Whisper 模型懒加载 | 启动秒开，下载在后台线程不阻塞事件循环 |
| 4 | 百炼 HTTP 响应解析支持两种格式 | 原始 JSON 行（实测格式）+ `data:` SSE 前缀（兼容） |
| 5 | 保留 Ollama 为 fallback | `AI_PROVIDER=ollama` 一键切换 |

---

## 遇到的问题

| # | 问题 | 解决方案 |
|---|------|---------|
| 1 | 百炼健康检查 400 — 缺 `enable_omni_output_audio_url` | 添加必填参数 |
| 2 | HuggingFace 下载极慢，终端卡死 | 切 ModelScope 下载 + 懒加载 + 后台线程 |
| 3 | `hf-mirror.com` 308 重定向不兼容 | 放弃镜像方案，改用 ModelScope SDK |
| 4 | `uv sync` 装 modelscope 时卸载 `sherpa-onnx-core` | 重新 `uv add sherpa-onnx`，修复 lockfile |
| 5 | sherpa-onnx C 扩展用 ORT 1.17 但模型要 1.20+ — ORT DLL 补丁在升级后失效 | 重写 `_fix_onnxruntime_dll()` 覆盖两种场景 |
| 6 | 百炼返回原始 JSON（非 SSE `data:` 前缀），代码全部跳过 | 修改解析为裸 JSON 行 |
| 7 | LLM 一次性返回完整文本但前端不显示 | 修复 `llmBufferRef` 空缓冲区 fallback 逻辑 |

---

## 验证结果

```
31 passed in 0.17s
Frontend TypeScript: zero errors
Ollama 模式完全向后兼容 ✅
百炼模式：health → ai_available: true ✅
Whisper large-v3 + CUDA: 中文识别正常 ✅
sherpa-onnx TTS: 语音合成正常 ✅
前端聊天框: AI 文字回复正常显示 ✅
语音对话全链路: VAD → ASR → Bailian → TTS → 播放 ✅
```

---

## 下一步

- [ ] PR 11: Agent 框架 + Agent 选择器 UI
- [ ] PR 12: 文档解析 + 实体提取服务
- [ ] PR 13: InterviewAgent 面试前 — 动态题库生成
- [ ] PR 14: InterviewAgent 面试中 — 全双工语音 + STAR 追问
- [ ] PR 15: InterviewAgent 面试后 — 结构化评分 + 报告
- [ ] PR 16: 端到端集成测试 + 文档完善
