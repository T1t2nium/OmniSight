# 2026-06-14: PR 8 — 系统提示词 + 沉浸式对话体验

**分支**: phase/8-system-prompt
**PR**: #8
**文件变更**: 5 files changed

## 完成事项
- [x] 新建 `prompts.py` — 集中管理系统提示词
- [x] `ollama_client.py` 注入系统提示词到每条对话的首条消息
- [x] `state.py` SessionState 添加 `history` 字段持久化多轮对话
- [x] `conversation.py` 返回更新后的对话历史
- [x] `ws.py` 加载/保存多轮对话历史（thread-safe via `call_soon_threadsafe`）
- [x] 视觉问题检测：`_is_visual_question()` 跳过非视觉问题的摄像头帧
- [x] 阿拉伯数字 → 中文转换（TTS 更清晰）
- [x] TTS 文本 Unicode 过滤扩展（仅保留可发音字符块）
- [x] 用户自定义系统提示词

## 技术决策
- **系统提示词首位注入**：ollama_client 中 `messages = [{"role": "system", ...}]` 确保小模型遵守指令
- **历史裁剪**：仅保留最近 8 条消息（4 轮对话），防止上下文漂移
- **`call_soon_threadsafe`**：`add_done_callback` 运行在非主线程，需线程安全调度 asyncio
- **数字转中文**：≤5 位数字转为中文，避免 TTS 口齿不清；长数字（电话号）保留原样

## 遇到的问题
- **多轮对话历史丢失**：`add_done_callback` 在非主线程运行，`asyncio.create_task` 静默失败 → 用 `loop.call_soon_threadsafe` 修复
- **AI 描述非视觉问题的画面**：添加 `_is_visual_question()` 正则过滤，但后续用户选择禁用以自行控制提示词

## 下一步
- 前端背景 UI 升级（Canvas 流场粒子替代呼吸灯）
