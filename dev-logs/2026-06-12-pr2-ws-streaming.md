# 2026-06-12: PR 2 — WebSocket 媒体流骨架

**分支**: phase/2-ws-streaming
**PR**: [#1](https://github.com/T1t2nium/OmniSight/pull/1)
**文件变更**: 30 files (+6240 / -35)

## 完成事项
- [x] 后端：Pydantic 消息模型（schemas.py）— WSMessage 信封 + 6 种 payload
- [x] 后端：PCM 缓冲管理（audio.py）— 按 session 累积 PCM16 字节
- [x] 后端：连接状态管理（state.py）— asyncio.Lock 线程安全
- [x] 后端：WebSocket `/ws` 端点（ws.py）— 接收循环 + 消息路由 + echo
- [x] 后端：main.py 挂载 ws router + logging 配置
- [x] 前端：TypeScript 类型定义（types/index.ts）— 镜像 Pydantic 模型
- [x] 前端：WebSocket 客户端（wsClient.ts）— 指数退避重连
- [x] 前端：AudioContext 单例（audioContext.ts）— 16000Hz + 工具函数
- [x] 前端：useWebSocket — React Hook 包装 WSClient 生命周期
- [x] 前端：useMediaStream — getUserMedia 封装（start/stop/toggle）
- [x] 前端：useVAD — @ricky0123/vad-web 集成 + encodeWAV + send
- [x] 前端：useAudioPlayer — 占位 Hook（PR 3 实现）
- [x] 前端：VideoPanel / AudioIndicator / ConnectionStatus / ControlBar / ChatLog 组件
- [x] 前端：App.tsx 重写 — 组合所有 hooks + 组件
- [x] 前端：App.css — 暗色主题完整布局
- [x] 前端：WASM 资产自托管（silero_vad_v5.onnx + ONNX Runtime WASM）到 public/
- [x] 前端：copy-wasm-assets.js postinstall 脚本
- [x] 文档：implementation-steps.md PR 1 checkbox 全部勾选
- [x] 文档：dev-logs 更新 PR 1 分支/PR 状态

## 技术决策
- **JSON-only 消息协议**：所有 WebSocket 消息用 JSON + base64 payload（匹配 tech-stack 文档 + Parlor 参考模式）
- **VAD 模型 v5**：使用最新的 Silero VAD v5 模型（512 frame samples，比 legacy 1536 更轻量）
- **自托管 WASM**：关闭 CDN 依赖，ONNX/WASM 文件直接放在 public/ 由 Vite 提供
- **指数退避重连**：1s→2s→4s→8s→16s→30s (capped)，±25% jitter，最多 10 次
- **会话管理**：前端 crypto.randomUUID() 生成 session_id，后端 dict 按 session 追踪

## 遇到的问题
1. **TS 类型错误：`stream` 不是 `RealTimeVADOptions` 的有效属性**
   - 原因：`@ricky0123/vad-web` 使用 `getStream` 回调而非 `stream` 属性
   - 解决：`getStream: () => Promise.resolve(stream)` 替代 `stream: stream`

2. **TS 类型错误：`Parameters<typeof WSClient.prototype.constructor>[1]` 返回 `Function` 类型**
   - 原因：严格模式下 `constructor` 类型推断为 `Function`，`Parameters<Function>` 无效
   - 解决：显式定义 `WSClientOptions` 接口

3. **`public/silero_vad_v5.onnx` 被 `.gitignore` 的 `*.onnx` 规则阻止**
   - 原因：通用的 `*.onnx` 忽略规则也匹配了 VAD 模型
   - 解决：添加 `!frontend/public/silero_vad_v5.onnx` 例外

## 编译验证
| 检查项 | 结果 |
|--------|------|
| `uv run python -c "from app.main import app"` | ✅ All imports OK |
| `npx tsc --noEmit` | ✅ 零错误 |
| `npm run build` | ✅ 74 modules, 1.82s |

## 待手动验证（RUN_ME）
- [ ] 浏览器摄像头+麦克风权限 → 预览正常
- [ ] VAD 检测：说话时 AudioIndicator 变红，安静时变绿
- [ ] ConnectionStatus 显示 "Connected"
- [ ] ChatLog 显示服务器 echo（音频时长、帧数统计）
- [ ] Toggle Camera/Mic 独立工作
- [ ] Stop/Start 对话重连正常

## 下一步
- PR 3：本地 AI 视觉对话核心（Ollama + faster-whisper + 全链路集成）
