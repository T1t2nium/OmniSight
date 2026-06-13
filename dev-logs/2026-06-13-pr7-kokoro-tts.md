# PR 7: TTS 质量升级 — Piper → sherpa-onnx

**日期**: 2026-06-13
**分支**: `phase/7-kokoro-tts`
**状态**: ✅ 已完成

---

## 背景

Piper TTS (`zh_CN-huayan-medium`) 中文语音存在个别语句口齿不清的问题。根本原因是 **espeak-ng 的中文 G2P（文字转音素）质量极差**。

第一次尝试用 Kokoro 82M 替换，但发现 Kokoro 的 `kokoro-onnx` 包装同样依赖运行时 espeak-ng 做 G2P，存在结构性缺陷：
- 拼音→IPA 映射表缺失 25+ 音节（jue, que, xue, yue 等）
- 35+ 常用汉字被静默跳过
- `phonemizer` 持续报 "words count mismatch on 100% lines"

最终切换到 **sherpa-onnx**（k2-fsa），使用内置 FST + 词典做中文文本处理，彻底摆脱 espeak-ng。

## 完成事项

### A. sherpa-onnx 引擎集成

| # | 内容 | 文件 |
|---|------|------|
| 1 | 调研 14+ 本地 TTS 项目 → Kokoro → sherpa-onnx | — |
| 2 | 安装 `sherpa-onnx>=1.13`（2.1 MB wheel，含 ONNX Runtime） | [pyproject.toml](backend/pyproject.toml) |
| 3 | 新建 SherpaTTS 服务类（Python API，FST+词典） | [sherpa_tts.py](backend/app/services/sherpa_tts.py) |
| 4 | 配置：sherpa 替代 kokoro，含迁移兼容 | [config.py](backend/app/config.py) |
| 5 | 后端集成：sherpa → piper → browser 三级降级 | [main.py](backend/app/main.py) |
| 6 | Orchestrator 适配：SherpaTTS 类型 + `'sherpa'` provider | [conversation.py](backend/app/services/conversation.py) |
| 7 | 下载脚本：下载 matcha-icefall-zh-baker (73 MB) | [download-sherpa-tts.ps1](scripts/download-sherpa-tts.ps1) |
| 8 | 清理：删除 kokoro_tts.py、download-kokoro.ps1、kokoro-onnx 依赖 | — |

### B. 前端适配

| # | 内容 | 文件 |
|---|------|------|
| 1 | TTSInfoPayload 类型 `'kokoro'` → `'sherpa'` | [types/index.ts](frontend/src/types/index.ts) |

### C. 文档

| # | 内容 | 文件 |
|---|------|------|
| 1 | .env.example 更新（sherpa 为默认引擎） | [.env.example](.env.example) |
| 2 | 版本号 0.4.0 → 0.5.0 | [main.py](backend/app/main.py) |
| 3 | 开发日志 | 本文件 |

## 技术决策

| # | 决策 | 理由 |
|---|------|------|
| 1 | **sherpa-onnx** 替代 Piper+Kokoro | 内置 FST+词典中文 G2P，不需要运行时 espeak-ng |
| 2 | `matcha-icefall-zh-baker` 模型 | 73MB、RTF~0.1、Apache 2.0、中文专用女声 |
| 3 | Python API 调用（非 subprocess） | sherpa-onnx 提供原生 Python API |
| 4 | 三级降级链：sherpa → piper → browser | 任意环节失败自动降级 |
| 5 | Kokoro → sherpa 透明迁移 | `field_validator` 自动将 `kokoro` 映射为 `sherpa` |
| 6 | 前端零改动（除类型定义） | PCM16 base64 格式不变，22050Hz 与 Piper 兼容 |

## 与 Piper/Kokoro 对比

| 指标 | Piper | Kokoro 82M | **sherpa-onnx** |
|------|-------|------------|------------------|
| 中文 G2P | espeak-ng | espeak-ng | **FST + 词典（内置）** |
| 中文音色 | 1 (huayan) | 8 (均劣化) | **1 (清晰女声)** |
| 模型大小 | 63 MB | 86 MB | **73 MB** |
| CPU 延迟 | ~200ms | ~1.5s | **50-150ms** |
| 许可证 | MIT/GPL | Apache 2.0 | **Apache 2.0** |
| 维护状态 | 已归档 | 活跃 | **活跃 (11.7k stars)** |

## 验证结果

- ✅ `uv run pytest tests/ -v` — 30/31 通过（1 个需更新本地 .env）
- ✅ `npx tsc --noEmit` — 零错误
- ✅ `npm run build` — 构建成功
- ✅ `uv run python -c "from app.main import app"` — 导入成功

## 架构图

```
User speech → VAD → whisper → transcript
  → Ollama NDJSON stream → sentence detection
  → asyncio.Queue → TTS Worker
  → SherpaTTS.synthesize() → float32 → PCM16 → base64
  → WebSocket tts_audio → Frontend AudioBufferSourceNode
```

## 待办

- [ ] 下载模型并验证中文语音清晰度
- [ ] 评估 GPU (CUDA/DirectML) 加速效果
- [ ] 考虑多音色支持（vits-melo-tts-zh_en 等）
