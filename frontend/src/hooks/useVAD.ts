import { useState, useEffect, useRef } from 'react';
import { arrayBufferToBase64 } from '../services/audioContext';
import type { WSMessage } from '../types';
import type { MicVAD } from '@ricky0123/vad-web';

export interface UseVADOptions {
  stream: MediaStream | null;
  sessionId: string;
  sendMessage: (msg: WSMessage) => void;
  enabled: boolean;
}

export interface UseVADReturn {
  isSpeaking: boolean;
  vadReady: boolean;
  vadError: string | null;
}

/**
 * Wraps @ricky0123/vad-web MicVAD in React lifecycle.
 *
 * Uses DYNAMIC import to avoid blocking page load — vad-web + onnxruntime-web
 * are loaded lazily only when the user starts a conversation.
 *
 * When enabled and a stream is available:
 *   - onSpeechStart → sends vad_event{speech_start}
 *   - onSpeechEnd   → encodes audio as WAV(base64) → sends audio_chunk
 */
export function useVAD({ stream, sessionId, sendMessage, enabled }: UseVADOptions): UseVADReturn {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [vadReady, setVadReady] = useState(false);
  const [vadError, setVadError] = useState<string | null>(null);
  const vadRef = useRef<MicVAD | null>(null);

  useEffect(() => {
    if (!stream || !enabled) {
      vadRef.current?.pause();
      setVadReady(false);
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        // Dynamic import — vad-web loads onnxruntime-web internally which
        // does its own WASM fetching and must not be pre-bundled by Vite.
        const { MicVAD: VAD, utils } = await import('@ricky0123/vad-web');

        // NOTE: Do NOT pass audioContext here — vad-web has a bug where
        // it skips assigning options.audioContext to this._audioContext,
        // causing "Audio context is null" error. Let the library create
        // its own AudioContext internally.
        const vad = await VAD.new({
          getStream: () => Promise.resolve(stream),
          startOnLoad: true,
          model: 'v5',
          // CDN paths for dev — ONNX runtime needs dynamic import() of .mjs
          // which doesn't work from Vite's public/ (static asset dir).
          // For production self-hosting, serve these via a reverse proxy or
          // configure Vite's build.rollupOptions to handle .wasm/.mjs assets.
          onnxWASMBasePath:
            'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.26.0/dist/',
          baseAssetPath:
            'https://cdn.jsdelivr.net/npm/@ricky0123/vad-web@0.0.29/dist/',
          processorType: 'ScriptProcessor',

          onSpeechStart: () => {
            if (cancelled) return;
            setIsSpeaking(true);
            sendMessage({
              type: 'vad_event',
              session_id: sessionId,
              timestamp: Date.now() / 1000,
              payload: { event: 'speech_start' },
            });
          },

          onSpeechEnd: (audio: Float32Array) => {
            if (cancelled) return;
            setIsSpeaking(false);

            // Encode Float32Array@16kHz → WAV (PCM16) → base64
            const wavBuffer = utils.encodeWAV(audio);
            const base64 = arrayBufferToBase64(wavBuffer);
            const durationMs = (audio.length / 16000) * 1000;

            sendMessage({
              type: 'audio_chunk',
              session_id: sessionId,
              timestamp: Date.now() / 1000,
              payload: {
                data: base64,
                sample_rate: 16000,
                channels: 1,
                duration_ms: Math.round(durationMs * 10) / 10,
              },
            });
          },

          onVADMisfire: () => {
            // Speech segment too short — silently ignored
          },
        });

        if (cancelled) {
          vad.destroy();
          return;
        }

        vadRef.current = vad;
        setVadReady(true);
        setVadError(null);
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'VAD initialisation failed';
          setVadError(message);
          setVadReady(false);
        }
      }
    })();

    return () => {
      cancelled = true;
      vadRef.current?.destroy();
      vadRef.current = null;
      setVadReady(false);
      setIsSpeaking(false);
    };
  }, [stream, enabled, sessionId, sendMessage]);

  return { isSpeaking, vadReady, vadError };
}
