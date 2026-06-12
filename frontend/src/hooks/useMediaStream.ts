import { useState, useRef, useCallback, useEffect } from 'react';
import { resumeAudioContext } from '../services/audioContext';

export interface UseMediaStreamReturn {
  stream: MediaStream | null;
  cameraEnabled: boolean;
  micEnabled: boolean;
  error: string | null;
  startMedia: () => Promise<void>;
  stopMedia: () => void;
  toggleCamera: () => Promise<void>;
  toggleMic: () => Promise<void>;
}

const AUDIO_CONSTRAINTS: MediaTrackConstraints = {
  sampleRate: 16000,
  channelCount: 1,
  echoCancellation: true,
  noiseSuppression: true,
};

/**
 * Manages getUserMedia lifecycle — camera + microphone access.
 * Handles start/stop and independent toggling of camera and mic tracks.
 */
export function useMediaStream(): UseMediaStreamReturn {
  const streamRef = useRef<MediaStream | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [micEnabled, setMicEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startMedia = useCallback(async () => {
    try {
      await resumeAudioContext();
      const s = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: AUDIO_CONSTRAINTS,
      });
      streamRef.current = s;
      setStream(s);
      setCameraEnabled(true);
      setMicEnabled(true);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to access media devices';
      setError(message);
    }
  }, []);

  const stopMedia = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setStream(null);
    setCameraEnabled(false);
    setMicEnabled(false);
  }, []);

  const toggleCamera = useCallback(async () => {
    if (cameraEnabled) {
      streamRef.current?.getVideoTracks().forEach((t) => t.stop());
      setCameraEnabled(false);
    } else {
      try {
        const s = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
        s.getVideoTracks().forEach((t) => {
          streamRef.current?.addTrack(t);
        });
        // Create a new stream reference so React detects the change
        if (streamRef.current) {
          setStream(new MediaStream(streamRef.current.getTracks()));
        }
        setCameraEnabled(true);
        setError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to access camera';
        setError(message);
      }
    }
  }, [cameraEnabled]);

  const toggleMic = useCallback(async () => {
    if (micEnabled) {
      streamRef.current?.getAudioTracks().forEach((t) => t.stop());
      setMicEnabled(false);
    } else {
      try {
        await resumeAudioContext();
        const s = await navigator.mediaDevices.getUserMedia({
          video: false,
          audio: AUDIO_CONSTRAINTS,
        });
        s.getAudioTracks().forEach((t) => {
          streamRef.current?.addTrack(t);
        });
        if (streamRef.current) {
          setStream(new MediaStream(streamRef.current.getTracks()));
        }
        setMicEnabled(true);
        setError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to access microphone';
        setError(message);
      }
    }
  }, [micEnabled]);

  // Cleanup all tracks on unmount
  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return {
    stream,
    cameraEnabled,
    micEnabled,
    error,
    startMedia,
    stopMedia,
    toggleCamera,
    toggleMic,
  };
}
