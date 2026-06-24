import { useEffect, useRef } from 'react';
import type { WSMessage } from '../types';

interface UseFrameCaptureOptions {
  stream: MediaStream | null;
  sessionId: string;
  sendMessage: (msg: WSMessage) => void;
  enabled: boolean;
  /** Target frames per second (default 4). */
  fps?: number;
  /** JPEG quality 0–1 (default 0.7). */
  quality?: number;
  /** Max width (canvas scales proportionally, default 640). */
  maxWidth?: number;
}

/**
 * Periodically captures JPEG frames from a MediaStream's video track
 * and sends them as video_frame messages over WebSocket.
 *
 * Creates an off-screen <canvas>, draws the video at the target FPS,
 * and sends the base64-encoded JPEG.
 */
export function useFrameCapture({
  stream,
  sessionId,
  sendMessage,
  enabled,
  fps = 4,
  quality = 0.7,
  maxWidth = 640,
}: UseFrameCaptureOptions): void {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!stream || !enabled) {
      if (intervalRef.current) {
        // Send a clear-frame message so the backend drops the
        // stale frame.  Without this the AI keeps seeing the
        // last captured image after the camera is turned off.
        sendMessage({
          type: 'video_frame',
          session_id: sessionId,
          timestamp: Date.now() / 1000,
          payload: { data: '', width: 0, height: 0 },
        });
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    const videoTrack = stream.getVideoTracks()[0];
    if (!videoTrack || videoTrack.readyState === 'ended') {
      return;
    }

    // Create an off-screen canvas (reused across captures)
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Need a <video> element to decode the stream for canvas drawing.
    // We reuse the same element across captures.
    const video = document.createElement('video');
    video.srcObject = stream;
    video.muted = true;
    video.playsInline = true;
    video.play().catch(() => {
      // Autoplay may fail if stream isn't ready yet; ignore
    });

    const captureAndSend = () => {
      if (video.readyState < video.HAVE_CURRENT_DATA) return;

      // Scale to maxWidth, preserve aspect ratio
      const scale = maxWidth / video.videoWidth;
      canvas.width = maxWidth;
      canvas.height = Math.round(video.videoHeight * scale);

      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      const jpegBase64 = canvas.toDataURL('image/jpeg', quality).split(',')[1];
      if (!jpegBase64) return;

      sendMessage({
        type: 'video_frame',
        session_id: sessionId,
        timestamp: Date.now() / 1000,
        payload: {
          data: jpegBase64,
          width: canvas.width,
          height: canvas.height,
        },
      });
    };

    // Capture at target FPS
    const intervalMs = Math.round(1000 / fps);
    intervalRef.current = setInterval(captureAndSend, intervalMs);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      video.pause();
      video.srcObject = null;
    };
    // sessionId is intentionally stable; only stream/enabled/fps change
  }, [stream, enabled, sessionId, sendMessage, fps, quality, maxWidth]);
}
