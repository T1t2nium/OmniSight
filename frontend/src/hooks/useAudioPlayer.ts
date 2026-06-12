/**
 * Audio playback hook — uses browser SpeechSynthesis API for TTS.
 *
 * PR 4 will upgrade to PCM16 audio queue playback via Web Audio API.
 */

import { useCallback, useRef } from 'react';

export interface UseAudioPlayerReturn {
  playAudio: (text: string) => Promise<void>;
  stopPlayback: () => void;
}

export function useAudioPlayer(): UseAudioPlayerReturn {
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const playAudio = useCallback(async (text: string) => {
    if (!text) return;

    // Cancel any previous utterance
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    // Try to find a Chinese voice if the system has one
    const voices = window.speechSynthesis.getVoices();
    const zhVoice = voices.find((v) => v.lang.startsWith('zh'));
    if (zhVoice) utterance.voice = zhVoice;

    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  }, []);

  const stopPlayback = useCallback(() => {
    window.speechSynthesis.cancel();
    utteranceRef.current = null;
  }, []);

  return { playAudio, stopPlayback };
}
