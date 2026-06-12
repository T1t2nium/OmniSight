/**
 * Audio playback hook — PCM16 Web Audio API queue (PR 4).
 *
 * Two modes:
 *   1. PCM16 queue: receives base64 PCM16 chunks from Piper TTS,
 *      decodes, converts to Float32, schedules via AudioBufferSourceNode.
 *      Each chunk plays sequentially with correct timing.
 *   2. SpeechSynthesis fallback: used when Piper is unavailable.
 *
 * Interrupt: stopPlayback() immediately stops current audio + clears queue.
 */

import { useCallback, useRef, useState } from 'react';

export interface UseAudioPlayerReturn {
  /** Enqueue base64 PCM16 audio for playback via Web Audio API. */
  playPCM16: (base64Data: string, sampleRate: number, text: string) => void;
  /** Fallback: speak text via browser SpeechSynthesis API. */
  playSpeechSynthesis: (text: string) => Promise<void>;
  /** Immediately stop all audio and clear the queue (barge-in). */
  stopPlayback: () => void;
  /** True while audio is playing via Web Audio API. */
  isSpeaking: boolean;
}

export function useAudioPlayer(): UseAudioPlayerReturn {
  const ctxRef = useRef<AudioContext | null>(null);
  const nextStartRef = useRef<number>(0);
  const currentSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const playingRef = useRef<boolean>(false);
  const queueRef = useRef<Array<{ buffer: AudioBuffer; text: string }>>([]);
  const [isSpeaking, setIsSpeaking] = useState(false);

  /** Lazy-init playback AudioContext (separate from VAD's 16kHz context). */
  const getCtx = useCallback((): AudioContext => {
    if (!ctxRef.current) {
      ctxRef.current = new AudioContext();
    }
    // Resume if suspended (browser autoplay policy)
    if (ctxRef.current.state === 'suspended') {
      ctxRef.current.resume();
    }
    return ctxRef.current;
  }, []);

  /** Decode base64 → bytes → Int16Array → Float32Array → AudioBuffer → enqueue. */
  const playPCM16 = useCallback(
    (base64Data: string, sampleRate: number, text: string) => {
      try {
        // base64 → binary string → Uint8Array → Int16Array
        const binaryStr = atob(base64Data);
        const byteLen = binaryStr.length;
        const bytes = new Uint8Array(byteLen);
        for (let i = 0; i < byteLen; i++) {
          bytes[i] = binaryStr.charCodeAt(i);
        }
        const int16 = new Int16Array(bytes.buffer);

        // Int16 → Float32 (normalized to [-1, 1])
        const float32 = new Float32Array(int16.length);
        for (let i = 0; i < int16.length; i++) {
          float32[i] = int16[i] / 32768.0;
        }

        const ctx = getCtx();
        const buffer = ctx.createBuffer(1, float32.length, sampleRate);
        buffer.getChannelData(0).set(float32);

        queueRef.current.push({ buffer, text });
        setIsSpeaking(true);

        // Start playing if idle
        if (!playingRef.current) {
          playNext(ctx);
        }
      } catch (err) {
        console.error('[AudioPlayer] PCM16 decode failed:', err);
      }
    },
    [getCtx],
  );

  /** Play the next buffer in the queue, or stop if empty. */
  const playNext = (ctx: AudioContext) => {
    const item = queueRef.current.shift();
    if (!item) {
      playingRef.current = false;
      nextStartRef.current = 0;
      setIsSpeaking(false);
      return;
    }

    playingRef.current = true;
    const now = ctx.currentTime;
    const startTime = Math.max(now, nextStartRef.current || now);

    const source = ctx.createBufferSource();
    source.buffer = item.buffer;
    source.connect(ctx.destination);
    source.start(startTime);

    nextStartRef.current = startTime + item.buffer.duration;
    currentSourceRef.current = source;

    source.onended = () => {
      if (currentSourceRef.current === source) {
        currentSourceRef.current = null;
      }
      playNext(ctx);
    };
  };

  /** Fallback: browser SpeechSynthesis (used when Piper is unavailable). */
  const playSpeechSynthesis = useCallback(async (text: string) => {
    if (!text) return;

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const zhVoice = voices.find((v) => v.lang.startsWith('zh'));
    if (zhVoice) utterance.voice = zhVoice;

    window.speechSynthesis.speak(utterance);
  }, []);

  /** Stop all playback immediately (for barge-in / interrupt). */
  const stopPlayback = useCallback(() => {
    // Stop Web Audio API playback
    if (currentSourceRef.current) {
      try {
        currentSourceRef.current.stop();
      } catch {
        // Already stopped — AudioBufferSourceNode can only be stopped once
      }
      currentSourceRef.current.disconnect();
      currentSourceRef.current = null;
    }

    // Clear queue and reset state
    queueRef.current.length = 0;
    playingRef.current = false;
    nextStartRef.current = 0;
    setIsSpeaking(false);

    // Also cancel any browser SpeechSynthesis
    window.speechSynthesis.cancel();
  }, []);

  return { playPCM16, playSpeechSynthesis, stopPlayback, isSpeaking };
}
