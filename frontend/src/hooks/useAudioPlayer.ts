/**
 * Audio playback hook — placeholder for PR 2.
 *
 * PR 3 will add actual PCM16 decode + AudioBufferSourceNode queue playback.
 * PR 4 will add barge-in / interrupt support.
 */

import { useCallback } from 'react';

export interface UseAudioPlayerReturn {
  playAudio: (base64Wav: string) => Promise<void>;
  stopPlayback: () => void;
}

export function useAudioPlayer(): UseAudioPlayerReturn {
  const playAudio = useCallback(async (_base64Wav: string) => {
    // Placeholder: PR 3 will decode base64 → AudioBuffer → play via Web Audio API
  }, []);

  const stopPlayback = useCallback(() => {
    // Placeholder: PR 4 will stop current playback and clear the queue
  }, []);

  return { playAudio, stopPlayback };
}
