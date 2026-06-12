/**
 * AudioContext singleton manager.
 *
 * Created lazily on first access because browsers block AudioContext creation
 * before a user gesture. Always call resumeAudioContext() inside a click handler.
 */

let audioContext: AudioContext | null = null;

export function getAudioContext(): AudioContext {
  if (!audioContext) {
    audioContext = new AudioContext({ sampleRate: 16000 });
  }
  return audioContext;
}

/** Must be called from a user gesture (e.g., button click). */
export async function resumeAudioContext(): Promise<void> {
  const ctx = getAudioContext();
  if (ctx.state === 'suspended') {
    await ctx.resume();
  }
}

/** Convert an ArrayBuffer to a base64 string for WebSocket transport. */
export function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}
