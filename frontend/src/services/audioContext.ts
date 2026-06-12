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

/** Convert an ArrayBuffer to a base64 string for WebSocket transport.
 *
 * Uses TextDecoder('latin1') for safe byte→character mapping.
 * The manual String.fromCharCode loop corrupts bytes > 127 because
 * JavaScript strings are UTF-16 and concatenation can produce multi-byte
 * code units that btoa cannot process correctly.
 */
export function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const binary = new TextDecoder('latin1').decode(new Uint8Array(buffer));
  return btoa(binary);
}
