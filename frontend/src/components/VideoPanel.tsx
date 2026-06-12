import { useRef, useEffect } from 'react';

interface VideoPanelProps {
  stream: MediaStream | null;
  cameraEnabled: boolean;
}

export function VideoPanel({ stream, cameraEnabled }: VideoPanelProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (video && stream) {
      video.srcObject = stream;
      video.play().catch(() => {
        // Browser may block autoplay; user gesture resolves this
      });
    }
  }, [stream]);

  if (!cameraEnabled || !stream) {
    return (
      <div className="video-panel video-placeholder">
        <div className="placeholder-text">Camera Off</div>
      </div>
    );
  }

  return (
    <div className="video-panel">
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
