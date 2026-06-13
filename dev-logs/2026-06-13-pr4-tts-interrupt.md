# 2026-06-13: PR 4 — TTS 升级 + 打断机制

**分支**: phase/4-tts-interrupt
**PR**: #3
**文件变更**: 17 files (7 backend, 5 frontend, 2 docs, 3 scripts)
**Commits**: 15

## 完成事项

- [x] 后端：PiperTTS 服务封装（subprocess.run + asyncio.to_thread，通用事件循环兼容）
- [x] 后端：split_sentences 工具函数（中英文句边界：。！？.!?\n）
- [x] 后端：ConversationOrchestrator 集成 TTS（生产者-消费者 Queue，LLM 流式 → 句检测 → TTS worker）
- [x] 后端：打断机制（speech_start → cancel pipeline task → send interrupt → 前端停止播放）
- [x] 后端：tts_info 信号（显式告知前端 TTS 提供方是 piper 还是 browser，消除竞态）
- [x] 后端：_clean_for_tts 清洗函数（去除 Markdown 格式字符，Piper 不会朗读 ** * - ` 等）
- [x] 后端：schemas 扩展（TTSAudioPayload, TTSInfoPayload, InterruptPayload）
- [x] 后端：config + main.py lifespan 初始化（graceful fallback to browser TTS）
- [x] 后端：版本号升至 0.3.0
- [x] 前端：useAudioPlayer 完全重写（PCM16 Web Audio API 队列 + SpeechSynthesis 回退）
- [x] 前端：App.tsx 集成 tts_audio 播放、tts_info 驱动、interrupt 清理、本地 barge-in
- [x] 前端：AudioIndicator 新增 AI 说话中状态（蓝色脉冲灯）
- [x] 前端：ChatLog 处理 tts_audio/interrupt（不渲染）
- [x] 脚本：download-piper.ps1（Piper exe + 中英文语音模型）
- [x] 脚本：download-xiao-ya.ps1（小雅中文语音下载）
- [x] 验证：`npx tsc --noEmit` 零错误，`npm run build` 成功，后端导入成功

## 技术决策

1. **subprocess.run + asyncio.to_thread**：放弃 asyncio.create_subprocess_exec（Windows uvicorn 事件循环 NotImplementedError），改用同步 subprocess 线程池化，兼容所有事件循环。

2. **生产者-消费者 TTS 队列**：LLM 流式生成（生产者）→ 句检测 → asyncio.Queue → 单一 TTS Worker（消费者）逐句合成发送。保证：
   - 句子顺序正确（FIFO 队列 + 单一 worker）
   - LLM 流不受阻塞（queue.put 非阻塞）
   - 第一句音频尽早到达（worker 并行运行）

3. **tts_info 显式信号**：放弃前端 500ms 计时器猜测，后端在流水线起始发送 tts_info(provider=piper|browser)，前端据此决定播放方式。消除 Piper TTS + SpeechSynthesis 双声线竞态。

4. **正确关闭 thinking 模式**：Ollama 原生参数是 `think: false`（v0.9.0+），而非 `enable_thinking: false`。后者被 Ollama 静默忽略。

5. **中文语音模型选择**：piper 2023.11.14-2 的 phonemizer 对 pinyin 音素类型（xiao_ya, chaowen）有 bug（多字符音素如 "ai" 触发 "not a single codepoint" 崩溃）。仅 espeak 音素类型（huayan）兼容。等 piper 更新后可切换。

## 遇到的问题与修复

| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 1 | 用户说话气泡不显示 | React 18 批量合并 `lastMessage` 状态更新 | 改用 `ws.onMessage()` 直接回调处理每条消息 |
| 2 | AI 回复 114s + 文字乱码 | TTS `await` 在 LLM 流循环内阻塞 HTTP 流消费 | TTS 移到 LLM 流结束后异步执行 |
| 3 | 双声线叠加（Piper + SpeechSynthesis） | `llm_response(done=true)` 先于 `tts_audio` 到达 | 发送 tts_info 显式信号，前端依此决定 |
| 4 | TTS 朗读顺序错乱 | asyncio.gather 并行，短句先完成先发送 | 改用生产者-消费者 Queue + 单一 worker |
| 5 | 口齿不清 | 多个 piper 子进程并抢占 CPU | 单一 worker 串行合成 |
| 6 | 读标点符号奇怪 | Piper 朗读 Markdown 格式字符 | 添加 `_clean_for_tts()` 清洗函数 |
| 7 | xiao_ya 模型崩溃 | piper 2023.11.14-2 pinyin phonemizer bug | 回退 huayan (espeak 类型)，等 piper 更新 |
| 8 | PIPER_SPEAKER 空字符串解析错误 | pydantic int\|None 无法解析 "" | field_validator 空字符串 → None |
| 9 | `enable_thinking` 被 Ollama 忽略 | 它根本不是 Ollama 原生参数 | 改用 `think: false` |

## 最终架构

```
User speech → VAD(speech_end) → audio PCM16
  → whisper.transcribe() → transcript → 前端 (蓝色气泡)

Pipeline 启动 → tts_info(provider=piper|browser) → 前端知道用什么TTS

Ollama NDJSON stream (think=false, 2-5s)
  → 逐 delta → llm_response → 前端流式灰色气泡
  → 句边界检测 → asyncio.Queue.put(sentence)
       ↓
  TTS Worker (单一协程，FIFO 消费)
    → _clean_for_tts(sentence) → 去除 Markdown 格式
    → _tts.synthesize() → subprocess.run(piper) via asyncio.to_thread
    → base64 PCM16 → tts_audio → WebSocket
    → 前端 AudioBufferSourceNode 队列播放 (正确顺序)

Interrupt (用户插话):
  前端: VAD(speech_start) → stopPlayback() (本地 0ms)
  后端: speech_start → task.cancel() → send interrupt
  前端: interrupt → 清理部分LLM文本 + 停止音频
```

## 模型兼容性

| 中文语音 | 音素类型 | piper 2023.11.14-2 | 状态 |
|---------|---------|-------------------|------|
| huayan | espeak | ✅ 兼容 | 当前使用 |
| xiao_ya | pinyin | ❌ 崩溃 | 需等 piper 更新 |
| chaowen | pinyin | ❌ 崩溃 | 需等 piper 更新 |

## 下一步

- PR 5：健壮性与体验优化（心跳、超时清理、错误边界、快捷键、测试）
