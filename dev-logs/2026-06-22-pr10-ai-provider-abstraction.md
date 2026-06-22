# PR 10: AI Provider 抽象层 + 百炼 HTTP 集成

**日期**: 2026-06-22  
**分支**: `phase/10-ai-provider-abstraction`  
**类型**: feat

## 完成事项

### 1. BaseAIClient 抽象协议 (`backend/app/services/base_ai_client.py`)
- 定义 `BaseAIClient` ABC，所有 AI Provider 必须实现的统一接口
- 抽象方法：`chat()`, `check_health()`, `close()`
- 抽象属性：`model`, `provider_name`
- 内置 `check_health_with_retry()` 默认实现（3 次重试，2s 间隔）

### 2. OllamaClient 重构
- 继承 `BaseAIClient` 并实现全部抽象方法
- 添加 `model` 属性和 `provider_name` 属性
- 内部逻辑完全不变，保持向后兼容

### 3. BailianHTTPClient (`backend/app/services/bailian_http_client.py`)
- 实现 `BaseAIClient` 接口
- 调用阿里云百炼 DashScope 多模态生成 API
- 通过 SSE (Server-Sent Events) 流式解析响应
- 支持文本 + 图片多模态输入（与 OllamaClient 相同的数据格式）
- 使用 httpx（已有依赖），无需额外安装 SDK
- 完整的错误处理：HTTP 错误、连接超时、认证失败

### 4. 配置更新 (`backend/app/config.py`)
- `ai_provider` 新增 `"bailian"` 选项
- 新增 `bailian_api_key` 和 `bailian_model` 配置项
- 默认模型：`qwen3.5-omni-plus-2026-03-15`

### 5. ConversationOrchestrator 更新
- `__init__` 参数从 `ollama: OllamaClient` 改为 `ai_client: BaseAIClient`
- 所有日志消息改为 provider-agnostic

### 6. main.py 更新
- 根据 `ai_provider` 设置自动选择初始化 `OllamaClient` 或 `BailianHTTPClient`
- Bailian 模式下验证 API Key 非空
- `app.state.ollama` → `app.state.ai_client`
- Health 端点返回 `ai_provider` 和 `ai_available`（替代 `ollama_available`）
- 版本号升级至 0.7.0

### 7. 测试更新
- Health 端点测试适配新格式（`ai_provider` + `ai_available`）
- 全部 31 个现有测试通过 ✅

### 8. 验证结果
```
31 passed in 0.17s
Frontend TypeScript: zero errors
Ollama 模式完全向后兼容
```

## 待办事项

- [ ] PR 11: Agent 框架 + Agent 选择器 UI
- [ ] PR 12: 文档解析 + 实体提取服务
- [ ] PR 13: InterviewAgent 面试前 — 动态题库生成
- [ ] PR 14: InterviewAgent 面试中 — 全双工语音 + STAR 追问
- [ ] PR 15: InterviewAgent 面试后 — 结构化评分 + 报告
- [ ] PR 16: 端到端集成测试 + 文档完善
