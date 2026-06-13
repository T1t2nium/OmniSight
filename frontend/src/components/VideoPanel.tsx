import { useRef, useEffect } from 'react';

interface VideoPanelProps {
  stream: MediaStream | null;
  cameraEnabled: boolean;
  /** Bumped on every track change — force re-bind (PR 5). */
  streamVersion: number;
}

export function VideoPanel({ stream, cameraEnabled, streamVersion }: VideoPanelProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (!stream || !cameraEnabled) {
      video.srcObject = null;
      return;
    }

    // Force Chrome to re-evaluate tracks by briefly nulling srcObject.
    video.srcObject = null;
    video.srcObject = stream;
    video.play().catch(() => {});
  }, [stream, cameraEnabled, streamVersion]);

  if (!cameraEnabled || !stream) {
    return (
      <div className="video-panel video-placeholder" aria-label="Camera preview">
        <span className="placeholder-icon" aria-hidden="true">📷</span>
        <div className="placeholder-text">Camera Off</div>
      </div>
    );
  }

  return (
    <div className="video-panel" aria-label="Camera preview">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="video-preview"
        style={{ transform: 'scaleX(-1)' }}
      />
    </div>
  );
}
