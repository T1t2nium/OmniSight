# 2026-06-13: PR 4 — TTS 升级 + 打断机制

**分支**: phase/4-tts-interrupt
**PR**: #3 (pending)
**文件变更**: 15 files changed (7 new/modified backend, 5 frontend, 2 docs, 1 script)

## 完成事项

- [x] 后端：PiperTTS 服务封装（asyncio 子进程调用 piper 可执行文件）
- [x] 后端：split_sentences 工具函数（检测中英文句边界：。！？.!?\n）
- [x] 后端：ConversationOrchestrator 集成 TTS（LLM 流式 → 逐句检测 → tts_audio）
- [x] 后端：打断机制（speech_start → cancel pipeline task → send interrupt）
- [x] 后端：schemas 扩展（TTSAudioPayload, InterruptPayload）
- [x] 后端：config 新增 Piper 配置项（executable/model/config/speaker）
- [x] 后端：main.py lifespan 初始化 PiperTTS，失败时优雅回退到浏览器 TTS
- [x] 后端：版本号升至 0.3.0
- [x] 前端：useAudioPlayer 完全重写（PCM16 Web Audio API 队列 + SpeechSynthesis 回退）
- [x] 前端：App.tsx 集成 tts_audio 播放、interrupt 处理、本地 barge-in
- [x] 前端：AudioIndicator 新增 AI 说话中状态（蓝色脉冲灯）
- [x] 前端：ChatLog 处理新消息类型（tts_audio/interrupt → 不渲染）
- [x] 脚本：download-piper.ps1（一键下载 Piper exe + 中英文语音模型）
- [x] 文档：implementation-steps.md 更新 PR 4 清单
- [x] 验证：`npx tsc --noEmit` 零错误，`npm run build` 成功，后端导入成功

## 技术决策

1. **Piper 子进程方案**：使用 piper 可执行文件通过 asyncio.create_subprocess_exec 调用，而非 piper-tts Python 绑定。理由：
   - 无 Python 依赖冲突（piper-tts 依赖 onnxruntime + piper-phonemize，Windows 编译复杂）
   - piper.exe 是静态编译的单文件，部署简单
   - OS 文件缓存使首次加载后的调用延迟可接受（~100-200ms/句）

2. **句子级流式 TTS**：LLM 生成过程中实时检测句边界，逐句合成并发送。用户看到文字流式出现，听到第一句音频时可能后续句子还在生成——实现"流式"体验。

3. **双重打断机制**：
   - **本地打断**：前端 VAD 检测到 speech_start → 立即停止音频播放（零延迟）
   - **服务端确认**：后端收到 speech_start → cancel 后台任务 → send interrupt → 前端清理部分 LLM 文本
   - 本地先行动，服务端确认，避免 WebSocket 往返延迟导致音频短暂继续播放

4. **优雅回退**：Piper 不可用时（模型未配置/可执行文件缺失），ConversationOrchestrator 自动跳过 TTS。前端检测无 tts_audio 时回退到浏览器 SpeechSynthesis API——确保基本功能始终可用。

5. **独立 AudioContext**：播放用 AudioContext 与 VAD 的 16kHz AudioContext 分离，使用浏览器默认采样率（通常 44.1kHz/48kHz），利用浏览器内置的重采样器处理 Piper 22050Hz → 原生采样率的转换。

## 架构要点

### 数据流（PR 4 完整流程）

```
User speech → VAD(speech_end) → audio PCM16
  → whisper.transcribe() → transcript → frontend (蓝色气泡)
  → ollama.chat(text + frame) → NDJSON stream
    → 逐 delta → llm_response (前端流式灰色气泡)
    → 检测句边界 → split_sentences()
      → piper.synthesize(sentence) → PCM16 bytes
        → base64 → tts_audio → WebSocket
          → 前端 AudioBufferSourceNode 队列播放
          
Interrupt (用户开始说话):
  前端: VAD(speech_start) → stopPlayback() (本地)
  后端: speech_start → task.cancel() → send interrupt
  前端: interrupt → 清理部分 LLM 文本 + 停止所有音频
```

### TTS 消息格式

```json
{
  "type": "tts_audio",
  "payload": {
    "data": "<base64 PCM16>",
    "sample_rate": 22050,
    "channels": 1,
    "text": "这是被朗读的句子。"
  }
}
```

### 前端 PCM16 解码链

```
base64 → atob() → Uint8Array → Int16Array (little-endian) → Float32Array (/32768)
→ AudioBuffer (channel 0) → AudioBufferSourceNode → audioContext.destination
→ 调度到 nextStartTime 实现无缝连续播放
```

## 遇到的问题

- **base64→Int16 直接迭代错误**：最初代码 `new Int16Array(pcmLen)` 然后逐 byte 填入——Int16Array 长度参数是元素数（每元素 2 bytes），导致数组长度翻倍。修正为 `Uint8Array → Int16Array(bytes.buffer)` 直接重解释内存。

## 下一步

- PR 5：健壮性与体验优化（心跳、超时清理、错误边界、快捷键、测试）

## 待办 / 阻塞

- 用户需运行 `scripts/download-piper.ps1` 下载 Piper 语音模型后才能体验本地 TTS
- 如未下载，系统自动回退到浏览器 SpeechSynthesis（功能完整但语音自然度较低）
