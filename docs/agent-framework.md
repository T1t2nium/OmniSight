# OmniSight Agent 框架

> 可扩展的多场景 AI 人格系统。通过定义不同的 Agent，让同一套 AI 管道服务于不同场景（日常聊天 / 面试官 / 未来扩展）。

## 概述

Agent 框架的核心思想：**不同的 system prompt 塑造不同的 AI 人格**。每个 Agent 封装了：
- **系统提示词** (`system_prompt`) — 定义 AI 的角色、行为准则、输出风格
- **UI 配置** (`ui_config`) — 告诉前端该显示哪些组件（上传区、题库、报告等）

前端通过 Agent 选择器切换 Agent，后端将对应的 system_prompt 注入 AI 管道。

```
AgentRegistry (单例)
  ├── ChatAgent (agent_id="chat")
  │     ├── system_prompt → VISUAL_CHAT_SYSTEM_PROMPT
  │     └── ui_config → { 纯聊天 UI }
  └── InterviewAgent (agent_id="interview")
        ├── system_prompt → INTERVIEW_SYSTEM_PROMPT (面试官人格)
        ├── ui_config → { show_document_upload, show_question_bank }
        └── 三阶段管线 → 面试前 → 面试中 → 面试后
```

## 架构

### BaseAgent (ABC)

**文件**: `backend/app/agents/base.py`

```python
class BaseAgent(ABC):
    @property
    def agent_id(self) -> str: ...       # 唯一标识
    @property
    def name(self) -> str: ...            # 中文名称
    @property
    def description(self) -> str: ...     # 简介
    @property
    def system_prompt(self) -> str: ...   # 系统提示词
    def get_ui_config(self) -> dict: ...  # 可选，前端 UI 配置
```

### AgentRegistry

单例注册表，存储所有已注册 Agent。

```python
AgentRegistry.register(agent)        # 注册 Agent
AgentRegistry.get("chat")           # 按 ID 获取
AgentRegistry.list_agents()         # 获取所有 Agent 的信息列表
AgentRegistry.default_agent_id()    # 默认 Agent ID ("chat")
```

### 管道集成

1. WebSocket 连接建立 ⇒ 发送 `agent_list` 到前端
2. 用户选择 Agent ⇒ 前端发送 `agent_select { agent_id }`
3. 后端存储到 `SessionState.selected_agent`
4. 每次 AI 推理时：
   ```python
   agent = AgentRegistry.get(session.selected_agent)
   system_prompt = agent.system_prompt if agent else DEFAULT_PROMPT
   await ai_client.chat(text=..., system_prompt=system_prompt)
   ```

## 如何添加新 Agent

### 第 1 步：创建 Agent 类

在 `backend/app/agents/` 下创建新的 Python 文件（或目录 + `__init__.py`）：

```python
from app.agents.base import BaseAgent

class MyAgent(BaseAgent):
    agent_id = "my-agent"
    name = "我的助手"
    description = "处理特定场景的 AI 助手"

    @property
    def system_prompt(self) -> str:
        return """你是一个专业的 XXX 助手。
        你的职责是...
        回答风格：...
        """

    def get_ui_config(self) -> dict:
        return {
            "show_document_upload": False,   # 是否需要文档上传区
            "show_question_bank": False,     # 是否需要题库面板
            "header_color": "#58a6ff",       # 前端标题色（CSS 颜色）
        }
```

### 第 2 步：在 main.py 注册

```python
# backend/app/main.py — lifespan()

from app.agents.my_agent import MyAgent

AgentRegistry.register(ChatAgent())
AgentRegistry.register(InterviewAgent())
AgentRegistry.register(MyAgent())  # ← 新增
```

### 第 3 步：前端自动展示

无需修改前端代码。`AgentSelector` 组件根据 `agent_list` 消息自动渲染所有已注册的 Agent。

### 第 4 步：如需特殊 UI

如果你的 Agent 需要特殊前端交互（如 InterviewAgent 的上传区、题库、报告），需要：
1. 在 `get_ui_config()` 中设置对应 flag
2. 在 `App.tsx` 中根据 flag 条件渲染组件
3. 处理相应的 WS 消息类型

## UI Config 契约

`get_ui_config()` 返回的字典支持以下键（所有可选）：

| 键 | 类型 | 说明 |
|----|------|------|
| `show_document_upload` | bool | 是否显示 JD/简历双区上传组件 |
| `show_question_bank` | bool | 是否显示题库下拉菜单 |
| `header_color` | str | 标题栏强调色（如 `"#10b981"`） |

前端组件根据这些 flag 条件渲染：

```tsx
const uic = agentUIConfig;
{uic.show_document_upload && <DocumentUpload ... />}
{uic.show_question_bank && <QuestionBank ... />}
```

## 会话隔离

每个 WebSocket 会话独立选择 Agent：

- 选择 Agent 时清除会话历史（`session.history = []`）
- 开始对话时发送 `reset_conversation` 清空上下文
- 多个并发会话可各自使用不同 Agent，互不干扰

## 当前 Agent 参考

| Agent | ID | System Prompt | UI 配置 |
|-------|-----|--------------|---------|
| **视觉聊天伴侣** | `chat` | `prompts.py` — `SYSTEM_PROMPT` | 仅聊天 UI，蓝色标题 |
| **企业海面助手** | `interview` | `agents/interview/agent.py` — `INTERVIEW_SYSTEM_PROMPT` | 文档上传 + 题库 + 面试三阶段，绿色标题 |

## 消息协议

Agent 相关的 WebSocket 消息：

| 方向 | type | payload | 触发时机 |
|------|------|---------|----------|
| s→c | `agent_list` | `{ agents: [{ agent_id, name, description, ui_config }] }` | 会话注册后立即发送 |
| c→s | `agent_select` | `{ agent_id: "chat" }` | 用户在 AgentSelector 中点击 |

## 面试管线流程

InterviewAgent 是框架的完整应用示例，覆盖三个阶段的完整管道：

```
面试前: document_upload → DocumentParser → EntityExtractor.match()
        → QuestionGenerator.generate() → question_bank

面试中: start_interview → build_interview_instructions()
        → 复用 ChatAgent 管道（STT → LLM → TTS）但注入面试 instructions
        → stop_interview → interview_stopped + transcript

面试后: _generate_interview_report() → InterviewScorer.generate_report()
        → interview_report → ReportViewer（雷达图 + 建议）
```

详见 [architecture.md](architecture.md) 流程 5-7。
