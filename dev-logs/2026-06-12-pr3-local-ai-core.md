# 2026-06-12: PR 3 — 本地 AI 视觉对话核心

**分支**: phase/3-local-ai-core
**PR**: [#2](https://github.com/T1t2nium/OmniSight/pull/2)
**Commits**: 12 (63a128b → 7bf0405)
**文件变更**: 16 files (+840 / -44 initial, ~12 follow-up fixes)

## 完成事项
- [x] 后端：config.py（Pydantic Settings 加载 .env）
- [x] 后端：AudioTranscriber（faster-whisper small, asyncio.to_thread, 阈值 disabled）
- [x] 后端：OllamaClient（httpx NDJSON 流解析, check_health, enable_thinking=False）
- [x] 后端：ConversationOrchestrator（PCM→float32→transcribe→chat→stream 编排）
- [x] 后端：WAV 解析器（手动解析 IEEE_FLOAT format tag 3 → PCM16）
- [x] 后端：schemas.py 扩展（TranscriptPayload, LLMResponsePayload, AIStatusPayload）
- [x] 后端：state.py 扩展（latest_frame, ai_status）
- [x] 后端：audio.py flush() 方法
- [x] 后端：ws.py speech_end 触发 AI pipeline（后台任务）, speech_start 清缓冲
- [x] 后端：main.py lifespan 初始化 AI 服务, /health 加 ollama_available
- [x] 前端：useAudioPlayer 实现（SpeechSynthesis TTS）
- [x] 前端：ChatLog 条件渲染（用户/AI 气泡, 流式光标, ai_status, error）
- [x] 前端：App.tsx llm_response delta 累积 + done=true 原地更新 + TTS 触发
- [x] 前端：types/index.ts 扩展（TranscriptPayload, LLMResponsePayload, AIStatusPayload）
- [x] 前端：vad_event echo 静音, ai_status 去重
- [x] 前端：VAD 参数调优（threshold, redemptionMs, preSpeechPadMs, minSpeechMs）
- [x] 前端：base64 编码修复（chunked fromCharCode.apply 替代 TextDecoder('latin1')）

## 技术决策
- **Whisper small 模型**：base 模型中文"你好"转录为"作词"，small 准确率达 75%+
- **Whisper 阈值 disabled**：`no_speech_threshold=None, log_prob_threshold=None` — base/small 模型对中文 log_prob 偏低，被默认阈值误判为静音
- **IEEE_FLOAT WAV 解析**：`utils.encodeWAV()` 产生格式标签 3（IEEE_FLOAT 32-bit），非 PCM16。手动解析 WAV 头，float32→int16 转换
- **base64 编码**：`TextDecoder('latin1')` 映射到 windows-1252 导致 btoa 抛异常。改用 chunked `String.fromCharCode.apply`
- **流式气泡原地更新**：done=true 时直接改流式消息的 done flag（而非删掉重建），避免 Ollama 额外空行覆盖已显示的文本
- **enable_thinking=False**：Qwen 模型默认 thinking 模式翻倍延迟，关闭后直接输出
- **browser SpeechSynthesis TTS**：初版用浏览器内置 TTS，PR 4 升级 Piper

## 遇到的问题
1. **WAV 解码后全是噪音**：根因是 `utils.encodeWAV()` 输出 IEEE_FLOAT WAV 格式（标签 3），后端按 PCM16 解析导致 float32 字节被误读。解决：手动解析 WAV 头，识别格式标签，float32→int16。

2. **btoa 抛 InvalidCharacterError**：`TextDecoder('latin1')` 实际映射到 windows-1252，字节 0x80-0x9F 转为超出 Latin-1 范围的字符。解决：chunked `String.fromCharCode.apply`。

3. **Whisper 对中文返回空转录**：默认 `no_speech_threshold=0.6` 过滤中文段。解决：三个阈值全部设为 None。

4. **speech_end 不触发**：`negativeSpeechThreshold: 0.35` 太高，背景噪音持续高于阈值。解决：降回 0.2。

5. **AI 气泡文本丢失**：Ollama 多条 done=true 空行 + React 删建气泡竞态。解决：流式气泡原地更新 done 标记 + 提前固化 finalText 变量。

## 编译验证
| 检查项 | 结果 |
|--------|------|
| 后端导入 | ✅ v0.2.0, routes: /ws, /health |
| TypeScript strict | ✅ 零错误 |
| Vite build | ✅ 76 modules |

## 运行验证
| 检查项 | 结果 |
|--------|------|
| Ollama model 可用 (qwen3.5:2b-bf16) | ✅ |
| VAD 检测 Speech/Listening | ✅ |
| Whisper 中文转录 | ✅ ("这是几"→"这是几页") |
| Ollama 视觉对话 + 流式气泡 | ✅ |
| SpeechSynthesis TTS 朗读 | ✅ |
| enable_thinking=False 低延迟 | ✅ |

## 下一步
- PR 4：本地 TTS 升级 (Piper) + 用户打断机制
