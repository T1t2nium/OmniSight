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
 * Chunked String.fromCharCode.apply approach — the most reliable
 * binary-to-base64 method in browsers. TextDecoder('latin1') maps
 * bytes 0x80-0x9F to windows-1252 characters (€, ‚, etc.) that
 * are outside Latin-1 range, causing btoa to throw.
 */
export function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  const CHUNK = 0x2000; // 8KB chunks, well within Function.apply argument limit
  const parts: string[] = [];
  for (let i = 0; i < bytes.length; i += CHUNK) {
    const chunk = bytes.subarray(i, i + CHUNK);
    parts.push(String.fromCharCode.apply(null, Array.from(chunk)));
  }
  return btoa(parts.join(''));
}
