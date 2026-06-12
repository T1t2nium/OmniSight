import { useState, useCallback, useRef, useEffect } from 'react';
import { VideoPanel } from './components/VideoPanel';
import { AudioIndicator } from './components/AudioIndicator';
import { ConnectionStatus } from './components/ConnectionStatus';
import { ControlBar } from './components/ControlBar';
import { ChatLog } from './components/ChatLog';
import { useWebSocket } from './hooks/useWebSocket';
import { useMediaStream } from './hooks/useMediaStream';
import { useVAD } from './hooks/useVAD';
import { useAudioPlayer } from './hooks/useAudioPlayer';
import { useFrameCapture } from './hooks/useFrameCapture';
import type {
  WSMessage,
  LLMResponsePayload,
  TTSAudioPayload,
  InterruptPayload,
} from './types';

/** Mute repetitive echo types (fired at high frequency). */
const MUTED_ECHO_TYPES = new Set([
  'video_frame',
  'vad_event:speech_start',
  'vad_event:speech_end',
]);

function App() {
  const [conversationActive, setConversationActive] = useState(false);
  const [chatMessages, setChatMessages] = useState<WSMessage[]>([]);
  const [totalFrames, setTotalFrames] = useState(0);
  const [totalAudioMs, setTotalAudioMs] = useState(0);
  const sessionIdRef = useRef<string>(crypto.randomUUID());
  const llmBufferRef = useRef<string>('');
  // PR 4: tracks whether Piper TTS audio was received for the current response
  const ttsActiveRef = useRef<boolean>(false);
  // PR 4: timer to delay SpeechSynthesis fallback (tts_audio may lag behind done=true)
  const ttsFallbackTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const media = useMediaStream();
  const ws = useWebSocket(sessionIdRef.current);
  const {
    playPCM16,
    playSpeechSynthesis,
    stopPlayback,
    isSpeaking: aiSpeaking,
  } = useAudioPlayer();
  const vad = useVAD({
    stream: media.stream,
    sessionId: sessionIdRef.current,
    sendMessage: ws.send,
    enabled: conversationActive && media.micEnabled,
  });

  useFrameCapture({
    stream: media.stream,
    sessionId: sessionIdRef.current,
    sendMessage: ws.send,
    enabled: conversationActive && media.cameraEnabled,
  });

  // PR 4: Immediately stop AI audio when user starts speaking (local barge-in).
  useEffect(() => {
    if (vad.isSpeaking) {
      stopPlayback();
    }
  }, [vad.isSpeaking, stopPlayback]);

  // ---- Stable refs for audio callbacks (avoids stale closures) ----
  const playPCM16Ref = useRef(playPCM16);
  playPCM16Ref.current = playPCM16;
  const playSpeechSynthesisRef = useRef(playSpeechSynthesis);
  playSpeechSynthesisRef.current = playSpeechSynthesis;
  const stopPlaybackRef = useRef(stopPlayback);
  stopPlaybackRef.current = stopPlayback;

  // ---- Process messages directly via onMessage (avoids React 18 batching issues) ----
  useEffect(() => {
    return ws.onMessage((msg: WSMessage) => {
      // Extract stats from echo payloads
      if (msg.type === 'echo') {
        const p = msg.payload as Record<string, unknown>;
        if (typeof p.total_frames === 'number') setTotalFrames(p.total_frames);
        if (typeof p.total_audio_ms === 'number') setTotalAudioMs(p.total_audio_ms);
        if (
          typeof p.received_type === 'string' &&
          MUTED_ECHO_TYPES.has(p.received_type)
        ) {
          return; // Skip high-frequency echoes
        }
      }

      // ---- PR 4: TTS Audio playback ----
      if (msg.type === 'tts_audio') {
        const p = msg.payload as unknown as TTSAudioPayload;
        // Cancel any pending SpeechSynthesis fallback (TTS won the race)
        if (ttsFallbackTimerRef.current) {
          clearTimeout(ttsFallbackTimerRef.current);
          ttsFallbackTimerRef.current = null;
        }
        ttsActiveRef.current = true;
        playPCM16Ref.current(p.data, p.sample_rate, p.text);
        return;
      }

      // ---- PR 4: Interrupt (server confirmed barge-in) ----
      if (msg.type === 'interrupt') {
        console.log('[App] Interrupt received:', (msg.payload as unknown as InterruptPayload).reason);
        stopPlaybackRef.current();
        if (ttsFallbackTimerRef.current) {
          clearTimeout(ttsFallbackTimerRef.current);
          ttsFallbackTimerRef.current = null;
        }
        llmBufferRef.current = '';
        setChatMessages((prev) =>
          prev.filter(
            (m) =>
              m.type !== 'llm_response' ||
              (m.payload as unknown as LLMResponsePayload).done === true,
          ),
        );
        return;
      }

      // ---- New transcript: user spoke → reset TTS state ----
      if (msg.type === 'transcript') {
        ttsActiveRef.current = false;
        if (ttsFallbackTimerRef.current) {
          clearTimeout(ttsFallbackTimerRef.current);
          ttsFallbackTimerRef.current = null;
        }
        setChatMessages((prev) => [...prev, msg]);
        return;
      }

      // Handle streaming LLM response
      if (msg.type === 'llm_response') {
        const p = msg.payload as unknown as LLMResponsePayload;
        if (!p.done) {
          // Accumulate deltas
          llmBufferRef.current += p.delta;
          // Replace or append streaming message in chat
          setChatMessages((prev) => {
            const last = prev[prev.length - 1];
            if (
              last &&
              last.type === 'llm_response' &&
              (last.payload as unknown as LLMResponsePayload).done === false
            ) {
              return [
                ...prev.slice(0, -1),
                {
                  ...last,
                  payload: {
                    delta: llmBufferRef.current,
                    done: false,
                    total_duration: 0,
                  },
                },
              ];
            }
            return [...prev, msg];
          });
          return;
        }
        // Final chunk — update the existing streaming message in-place
        if (!llmBufferRef.current) return;
        const finalText = llmBufferRef.current;
        const finalDuration = p.total_duration;
        llmBufferRef.current = '';

        // PR 4: Defer SpeechSynthesis fallback — Piper TTS audio may
        // still be in transit (tts_audio is sent after LLM stream ends).
        // If no tts_audio arrives within 500ms, fall back to browser TTS.
        if (ttsFallbackTimerRef.current) {
          clearTimeout(ttsFallbackTimerRef.current);
        }
        ttsFallbackTimerRef.current = setTimeout(() => {
          if (!ttsActiveRef.current) {
            playSpeechSynthesisRef.current(finalText);
          }
          ttsFallbackTimerRef.current = null;
        }, 500);
        ttsActiveRef.current = false;

        setChatMessages((prev) => {
          for (let i = prev.length - 1; i >= 0; i--) {
            if (
              prev[i].type === 'llm_response' &&
              (prev[i].payload as unknown as LLMResponsePayload).done === false
            ) {
              const updated = [...prev];
              updated[i] = {
                ...updated[i],
                payload: {
                  delta: finalText,
                  done: true,
                  total_duration: finalDuration,
                },
              };
              return updated;
            }
          }
          return [
            ...prev,
            {
              type: 'llm_response',
              session_id: msg.session_id,
              timestamp: msg.timestamp,
              payload: {
                delta: finalText,
                done: true,
                total_duration: finalDuration,
              },
            },
          ];
        });
        return;
      }

      // Deduplicate ai_status — replace previous instead of appending
      if (msg.type === 'ai_status') {
        setChatMessages((prev) => {
          const filtered = prev.filter((m) => m.type !== 'ai_status');
          return [...filtered, msg];
        });
        return;
      }

      // Generic append for all other message types
      setChatMessages((prev) => [...prev, msg]);
    });
  }, [ws.onMessage]);

  const handleStartConversation = useCallback(async () => {
    await media.startMedia();
    setConversationActive(true);
  }, [media]);

  const handleStopConversation = useCallback(() => {
    media.stopMedia();
    stopPlaybackRef.current();
    setConversationActive(false);
    setChatMessages([]);
    setTotalFrames(0);
    setTotalAudioMs(0);
    llmBufferRef.current = '';
    ttsActiveRef.current = false;
  }, [media]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>OmniSight</h1>
        <span className="app-subtitle">AI Visual Conversation Assistant</span>
      </header>

      <main className="app-main">
        <div className="layout-top">
          <VideoPanel
            stream={media.stream}
            cameraEnabled={media.cameraEnabled}
          />
        </div>

        <div className="layout-status">
          <AudioIndicator
            isSpeaking={vad.isSpeaking}
            vadReady={vad.vadReady}
            micEnabled={media.micEnabled}
            aiSpeaking={aiSpeaking}
          />
          {conversationActive && (
            <span className="stats">
              Frames: {totalFrames} &middot; Audio:{' '}
              {(totalAudioMs / 1000).toFixed(1)}s
            </span>
          )}
          <ConnectionStatus state={ws.connectionState} />
          {media.error && <span className="media-error">{media.error}</span>}
          {vad.vadError && (
            <span className="vad-error">VAD: {vad.vadError}</span>
          )}
        </div>

        <div className="layout-chat">
          <ChatLog messages={chatMessages} />
        </div>

        <div className="layout-bottom">
          <ControlBar
            conversationActive={conversationActive}
            cameraEnabled={media.cameraEnabled}
            micEnabled={media.micEnabled}
            onStartConversation={handleStartConversation}
            onStopConversation={handleStopConversation}
            onToggleCamera={media.toggleCamera}
            onToggleMic={media.toggleMic}
          />
        </div>
      </main>
    </div>
  );
}

export default App;
