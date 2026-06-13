"""Unit tests — audio buffer, WAV parsing, sentence splitting, TTS cleaning."""

from __future__ import annotations

import struct

import numpy as np
import pytest

from app.services.audio import AudioBufferManager
from app.services.tts import split_sentences
from app.services.conversation import _clean_for_tts
from app.routes.ws import _parse_wav_to_pcm16


# ============================================================
# AudioBufferManager
# ============================================================


class TestAudioBufferManager:
    def test_add_and_get_audio(self, sample_pcm16):
        mgr = AudioBufferManager()
        mgr.add_audio("s1", sample_pcm16[:1600], 100)
        mgr.add_audio("s1", sample_pcm16[1600:3200], 100)
        total, dur = mgr.get_audio("s1")
        assert len(total) == 3200
        assert total == sample_pcm16[:3200]
        assert dur == 200

    def test_flush_clears_buffer(self, sample_pcm16):
        mgr = AudioBufferManager()
        mgr.add_audio("s1", sample_pcm16[:1600], 100)
        audio, duration = mgr.flush("s1")
        assert len(audio) == 1600
        assert duration == 100
        # Buffer should be empty after flush
        remaining, rdur = mgr.get_audio("s1")
        assert len(remaining) == 0

    def test_clear_removes_all(self, sample_pcm16):
        mgr = AudioBufferManager()
        mgr.add_audio("s1", sample_pcm16[:800], 50)
        mgr.add_audio("s2", sample_pcm16[:800], 50)
        mgr.clear("s1")
        audio, _ = mgr.get_audio("s1")
        assert len(audio) == 0
        audio2, _ = mgr.get_audio("s2")
        assert len(audio2) == 800

    def test_missing_session_returns_empty(self):
        mgr = AudioBufferManager()
        audio, _ = mgr.get_audio("nope")
        assert audio == b""
        audio, dur = mgr.flush("nope")
        assert audio == b""
        assert dur == 0.0


# ============================================================
# WAV Parser
# ============================================================


class TestWavParser:
    def test_ieee_float_to_pcm16(self, silent_wav_ieee_float):
        """Silent IEEE_FLOAT WAV → PCM16 bytes (all zeros)."""
        pcm = _parse_wav_to_pcm16(silent_wav_ieee_float)
        # 960 float samples → 960 int16 samples → 1920 bytes
        assert len(pcm) == 960 * 2
        # Should be all zeros (silence)
        arr = np.frombuffer(pcm, dtype=np.int16)
        np.testing.assert_array_equal(arr, np.zeros(960, dtype=np.int16))

    def test_ieee_float_nonzero_roundtrip(self):
        """Synthesize a WAV with known float values → verify PCM16 output."""
        import struct

        sample_rate = 16000
        num_samples = 100
        data_size = num_samples * 4
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + data_size, b"WAVE",
            b"fmt ", 16, 3, 1, sample_rate,
            sample_rate * 4, 4, 32,
            b"data", data_size,
        )
        # Sine wave, amplitude 0.5
        t = np.arange(num_samples) / sample_rate
        wave = (0.5 * np.sin(2.0 * np.pi * 440.0 * t)).astype(np.float32)
        wav = header + wave.tobytes()

        pcm = _parse_wav_to_pcm16(wav)
        arr = np.frombuffer(pcm, dtype=np.int16)
        # Should be non-zero (sine wave)
        assert np.abs(arr).max() > 0

    def test_pcm_passthrough(self):
        """PCM16 WAV should pass through unchanged."""
        import struct

        sample_rate = 16000
        num_samples = 100
        pcm_data = (np.arange(num_samples, dtype=np.int16) % 1000 - 500).tobytes()
        data_size = num_samples * 2
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + data_size, b"WAVE",
            b"fmt ", 16, 1, 1, sample_rate,
            sample_rate * 2, 2, 16,
            b"data", data_size,
        )
        wav = header + pcm_data
        result = _parse_wav_to_pcm16(wav)
        assert result == pcm_data

    def test_too_short_input(self):
        with pytest.raises(ValueError, match="too short|Not a valid"):
            _parse_wav_to_pcm16(b"short")

    def test_non_wav_input(self):
        with pytest.raises(ValueError):
            _parse_wav_to_pcm16(b"x" * 100)


# ============================================================
# Sentence Splitting
# ============================================================


class TestSentenceSplitter:
    def test_chinese_period_split(self):
        sentences, rest = split_sentences("你好。世界。")
        assert sentences == ["你好。", "世界。"]
        assert rest == ""

    def test_chinese_question_split(self):
        sentences, rest = split_sentences("你好吗？我很好。")
        assert sentences == ["你好吗？", "我很好。"]
        assert rest == ""

    def test_chinese_exclamation_split(self):
        sentences, rest = split_sentences("太好了！真的吗？是的。")
        assert sentences == ["太好了！", "真的吗？", "是的。"]
        assert rest == ""

    def test_incomplete_sentence(self):
        sentences, rest = split_sentences("今天天气")
        assert sentences == []
        assert rest == "今天天气"

    def test_mixed_ends_with_incomplete(self):
        sentences, rest = split_sentences("你好。我在想")
        assert sentences == ["你好。"]
        assert rest == "我在想"

    def test_english_sentences(self):
        sentences, rest = split_sentences("Hello world. How are you? I am fine!")
        assert sentences == ["Hello world.", "How are you?", "I am fine!"]
        assert rest == ""

    def test_empty_input(self):
        sentences, rest = split_sentences("")
        assert sentences == []
        assert rest == ""

    def test_whitespace_only(self):
        sentences, rest = split_sentences("   ")
        assert sentences == []
        assert rest == ""


# ============================================================
# TTS Markdown Cleaning
# ============================================================


class TestTtsClean:
    def test_bold_removed(self):
        assert _clean_for_tts("**hello** world") == "hello world"

    def test_italic_removed(self):
        assert _clean_for_tts("*hello* world") == "hello world"

    def test_list_markers_removed(self):
        result = _clean_for_tts("- item one\n- item two")
        assert "- " not in result
        assert "item one" in result

    def test_code_blocks_removed(self):
        result = _clean_for_tts("Use `print()` function")
        assert "`print()`" not in result

    def test_mixed_markdown(self):
        result = _clean_for_tts("**Bold** and *italic* and `code`")
        assert "*" not in result
        assert "`" not in result

    def test_empty_input(self):
        assert _clean_for_tts("") == ""

    def test_plain_text_passthrough(self):
        text = "Hello, this is plain text."
        assert _clean_for_tts(text) == text
