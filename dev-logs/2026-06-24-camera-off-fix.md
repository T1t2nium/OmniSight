# BugFix — 关闭摄像头后 AI 仍声称能看到画面

**日期**: 2026-06-24
**Commits**: cf22c2c, 6404bf8, 010f79c, a22a243
**状态**: ✅ 已修复

---

## 问题

选择「视觉聊天伴侣」开始对话后手动关闭摄像头，AI 仍然响应"能看到画面"——原因是为关闭摄像头后 `SessionState.latest_frame` 残留旧帧数据，且 AI 不知道摄像头已关。

## 修复（三轮迭代）

### 第一轮：清空残留帧（cf22c2c）

- **前端** `useFrameCapture.ts`：帧捕获循环停止时发送 `video_frame` 清帧信号（data="" width=0 height=0）
- **后端** `state.py`：新增 `clear_latest_frame()` 方法
- **后端** `ws.py`：`_handle_video_frame` 识别清帧信号 → `latest_frame = None`
- **测试**：`test_video_frame_clear_clears_latest_frame`（136 通过）

### 第二轮：告知 AI 摄像头状态（6404bf8）

仅清空帧不够——AI 收不到图片却不知道自己"应该看不到"，仍可能基于对话上下文虚构画面。

- **修复**：`process_utterance` 新增 `vision_enabled` 参数。当 `vision_enabled=True` 但 `latest_frame_b64=None` 时，在发给 AI 的文本末尾追加系统提示：
  ```
  [系统提示：摄像头已关闭，你当前无法看到任何画面。
  请勿描述或假装看到视频内容，基于对话历史和知识作答。]
  ```
- **设计**：仅修改 AI 输入，前端 transcript 和历史记录保持原样

### 第三轮：管道日志（010f79c）

添加全链路 console 日志，每轮对话可见完整决策链：

| 日志 | 位置 | 含义 |
|------|------|------|
| `📷 FRAME STORED` | `_handle_video_frame` | 收到正常帧 |
| `📷 CAMERA OFF` | `_handle_video_frame` | 收到清帧信号 |
| `🖼️ / 🚫 PIPELINE` | `_start_ai_pipeline` | 本轮是否带图片 |
| `💬 AI INPUT` | `process_utterance` | 发给 AI 的完整文字 |
| `🤖 AI RESPONSE` | `process_utterance` | AI 回复全文 |

### 第四轮：修复清帧信号未送达（a22a243）

React `useEffect` 生命周期顺序问题：当 `enabled: true→false` 时 React **先执行上次的 cleanup（将 `intervalRef.current` 置 null），再执行新 effect body**——此时 `intervalRef.current` 已是 null，清帧信号永远不会发送。

- **修复**：将 `sendMessage` 移入 cleanup 函数内部，确保它在 `intervalRef` 被清空前执行

## 涉及文件

| 文件 | 变更 |
|------|------|
| `frontend/src/hooks/useFrameCapture.ts` | 清帧信号在 cleanup 中发送 |
| `backend/app/routes/ws.py` | 清帧处理 + 管道日志 |
| `backend/app/models/state.py` | `clear_latest_frame()` |
| `backend/app/services/conversation.py` | 摄像头关闭提示注入 AI + 响应日志 |
| `backend/tests/test_ws.py` | `test_video_frame_clear_clears_latest_frame` |

## 测试结果

- ✅ 136/136 后端测试
- ✅ tsc 零错误
- ✅ 14/14 vitest
