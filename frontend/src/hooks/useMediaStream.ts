import { useState, useRef, useCallback, useEffect } from 'react';
import { resumeAudioContext } from '../services/audioContext';

export interface UseMediaStreamReturn {
  /** Main stream — for VideoPanel / frame capture. */
  stream: MediaStream | null;
  /** Audio-only stream — for VAD. Isolated from main stream so VAD's
   *  internal pause/destroy never touches video tracks. */
  vadStream: MediaStream | null;
  /** Bumped after every track change — VideoPanel uses this to force re-bind. */
  streamVersion: number;
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
 * Manages getUserMedia lifecycle.
 *
 * PR 5: VAD gets its own audio-only stream built from cloned audio tracks.
 * This prevents vad-web's pause/destroy from ever touching video tracks.
 */
export function useMediaStream(): UseMediaStreamReturn {
  const streamRef = useRef<MediaStream | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [vadStream, setVadStream] = useState<MediaStream | null>(null);
  const [streamVersion, setStreamVersion] = useState(0);
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [micEnabled, setMicEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** Build a fresh audio-only stream from cloned audio tracks. */
  function _syncVad(audioTracks: MediaStreamTrack[]) {
    // Stop any existing cloned tracks in the old VAD stream
    // (they are clones, so stopping them doesn't affect the originals)
    // No — we just create a fresh stream; old tracks get orphaned.
    const clones = audioTracks.map((t) => t.clone());
    setVadStream(new MediaStream(clones));
  }

  const startMedia = useCallback(async () => {
    try {
      await resumeAudioContext();
      const s = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: AUDIO_CONSTRAINTS,
      });
      streamRef.current = s;
      setStream(s);
      setStreamVersion((v) => v + 1);
      _syncVad(s.getAudioTracks());
      setCameraEnabled(true);
      setMicEnabled(true);
      setError(null);
    } catch (err) {
      const domErr = err as DOMException;
      let message: string;
      if (domErr.name === 'NotAllowedError') {
        message = 'Camera/Mic permission denied. Please allow access in browser settings.';
      } else if (domErr.name === 'NotFoundError') {
        message = 'No camera or microphone found. Please connect a device.';
      } else {
        message = err instanceof Error ? err.message : 'Failed to access media devices';
      }
      setError(message);
    }
  }, []);

  const stopMedia = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setStream(null);
    setVadStream(null);
    setStreamVersion((v) => v + 1);
    setCameraEnabled(false);
    setMicEnabled(false);
  }, []);

  const toggleCamera = useCallback(async () => {
    const st = streamRef.current;
    if (!st) return;

    if (cameraEnabled) {
      st.getVideoTracks().forEach((t) => { t.stop(); st.removeTrack(t); });
      setCameraEnabled(false);
      setStreamVersion((v) => v + 1);
    } else {
      try {
        const s = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        s.getVideoTracks().forEach((t) => st.addTrack(t));
        setCameraEnabled(true);
        setStreamVersion((v) => v + 1);
        setError(null);
      } catch (err) {
        const domErr = err as DOMException;
        setError(
          domErr.name === 'NotAllowedError'
            ? 'Camera permission denied. Please allow access in browser settings.'
            : err instanceof Error ? err.message : 'Failed to access camera',
        );
      }
    }
  }, [cameraEnabled]);

  const toggleMic = useCallback(async () => {
    const st = streamRef.current;
    if (!st) return;

    if (micEnabled) {
      // ---- Turn mic OFF ----
      st.getAudioTracks().forEach((t) => { t.stop(); st.removeTrack(t); });
      _syncVad([]); // empty VAD stream
      setMicEnabled(false);
      setStreamVersion((v) => v + 1);
    } else {
      // ---- Turn mic ON ----
      try {
        await resumeAudioContext();
        const s = await navigator.mediaDevices.getUserMedia({ video: false, audio: AUDIO_CONSTRAINTS });
        s.getAudioTracks().forEach((t) => st.addTrack(t));
        _syncVad(st.getAudioTracks());
        setMicEnabled(true);
        setStreamVersion((v) => v + 1);
        setError(null);
      } catch (err) {
        const domErr = err as DOMException;
        setError(
          domErr.name === 'NotAllowedError'
            ? 'Microphone permission denied. Please allow access in browser settings.'
            : err instanceof Error ? err.message : 'Failed to access microphone',
        );
      }
    }
  }, [micEnabled]);

  // Cleanup all tracks on unmount
  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return { stream, vadStream, streamVersion, cameraEnabled, micEnabled, error, startMedia, stopMedia, toggleCamera, toggleMic };
}
