# PR 7: TTS 质量升级 — Piper → Kokoro 82M

**日期**: 2026-06-13
**分支**: `phase/7-kokoro-tts`
**状态**: ✅ 已完成

---

## 背景

Piper TTS (`zh_CN-huayan-medium`) 中文语音存在个别语句口齿不清的问题：
- 单一中文语音（huayan），无音色选择
- espeak 音素器对中文处理粗糙
- xiao_ya（pinyin 音素）模型因 Piper 2023.11.14-2 版本 bug 崩溃
- Piper 项目已归档（Rhasspy），不再维护

## 完成事项

### A. Kokoro 引擎集成

| # | 内容 | 文件 |
|---|------|------|
| 1 | 调研 14+ 本地 TTS 项目，选择 Kokoro 82M | — |
| 2 | 安装 `kokoro-onnx>=0.5.0` + `soundfile` 依赖 | [pyproject.toml](backend/pyproject.toml) |
| 3 | 新建 KokoroTTS 服务类（Python API，非 subprocess） | [kokoro_tts.py](backend/app/services/kokoro_tts.py) |
| 4 | 配置扩展：新增 kokoro_* 5 个配置项 | [config.py](backend/app/config.py) |
| 5 | 后端集成：Kokoro → Piper → Browser 三级降级链 | [main.py](backend/app/main.py) |
| 6 | Orchestrator 适配：支持 KokoroTTS 类型 | [conversation.py](backend/app/services/conversation.py) |
| 7 | 下载脚本：自动下载 ONNX 模型 + 语音包 | [download-kokoro.ps1](scripts/download-kokoro.ps1) |

### B. 前端适配

| # | 内容 | 文件 |
|---|------|------|
| 1 | TTSInfoPayload 新增 `'kokoro'` 类型 | [types/index.ts](frontend/src/types/index.ts) |

### C. 文档

| # | 内容 | 文件 |
|---|------|------|
| 1 | .env.example 更新（Kokoro 为默认引擎） | [.env.example](.env.example) |
| 2 | 版本号 0.4.0 → 0.5.0 | [main.py](backend/app/main.py) |
| 3 | 开发日志 | 本文件 |

## 技术决策

| # | 决策 | 理由 |
|---|------|------|
| 1 | **Kokoro 82M** 替代 Piper | 100+ 中文音色、Apache 2.0 许可证、相同 ONNX 基础设施 |
| 2 | Python 库调用（非 subprocess） | `kokoro-onnx` 提供直接 API，更快更稳定 |
| 3 | 三级降级链：Kokoro → Piper → Browser | 任意环节失败自动降级，保证服务可用 |
| 4 | int8 量化模型（86 MB） | CPU 推理速度最佳，质量损失可忽略 |
| 5 | 默认中文语音 `zf_xiaobei` | v1.0 模型中最稳定的女声 |
| 6 | 前端零改动（除类型定义） | PCM16 base64 格式不变，完全兼容 |

## 与 Piper 对比

| 指标 | Piper | Kokoro 82M |
|------|-------|------------|
| 中文音色数 | 1 (huayan) | 8 (v1.0) / 100+ (v1.1-zh) |
| 模型大小 | 63 MB | 86 MB (int8) |
| 调用方式 | subprocess.run() | Python API |
| 采样率 | 22050 Hz | 24000 Hz |
| 许可证 | MIT/GPL 模糊 | Apache 2.0 |
| 维护状态 | 已归档 | 活跃 (2026) |

## 验证结果

- ✅ `uv run pytest tests/ -v` — 31/31 全绿
- ✅ `npx tsc --noEmit` — 零错误
- ✅ `npm run build` — 构建成功
- ✅ `uv run python -c "from app.main import app"` — 导入成功

## 架构图

```
User speech → VAD → whisper → transcript
  → Ollama NDJSON stream → sentence detection
  → asyncio.Queue → TTS Worker
  → KokoroTTS.synthesize() → float32 → PCM16 → base64
  → WebSocket tts_audio → Frontend AudioBufferSourceNode
```

## 待办

- [ ] 测试 v1.1-zh 中文增强模型（100+ 音色）
- [ ] 评估 GPU (DirectML) 加速效果
- [ ] 支持用户切换音色（通过配置或前端 UI）
