import { useState, useEffect, useRef } from 'react';
import { MicVAD, utils } from '@ricky0123/vad-web';
import { getAudioContext } from '../services/audioContext';
import { arrayBufferToBase64 } from '../services/audioContext';
import type { WSMessage } from '../types';

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
 * When enabled and a stream is available, initialises the VAD and:
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
        const audioContext = getAudioContext();

        const vad = await MicVAD.new({
          audioContext,
          getStream: () => Promise.resolve(stream),
          startOnLoad: true,
          model: 'v5',

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
