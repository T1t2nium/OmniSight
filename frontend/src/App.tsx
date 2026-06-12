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
import type { WSMessage, LLMResponsePayload } from './types';

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

  const media = useMediaStream();
  const ws = useWebSocket(sessionIdRef.current);
  const { playAudio, stopPlayback } = useAudioPlayer();
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

  // Process incoming messages: update stats, handle AI pipeline messages
  useEffect(() => {
    const msg = ws.lastMessage;
    if (!msg) return;

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
                payload: { delta: llmBufferRef.current, done: false, total_duration: 0 },
              },
            ];
          }
          return [...prev, msg];
        });
        return;
      }
      // Final chunk — speak, remove ALL previous llm_response messages,
      // append the final accumulated result.
      // Guard: Ollama may emit extra done=true lines with empty content.
      if (!llmBufferRef.current) return;
      playAudio(llmBufferRef.current);
      setChatMessages((prev) => [
        ...prev.filter((m) => m.type !== 'llm_response'),
        {
          type: 'llm_response',
          session_id: msg.session_id,
          timestamp: msg.timestamp,
          payload: {
            delta: llmBufferRef.current,
            done: true,
            total_duration: p.total_duration,
          },
        },
      ]);
      llmBufferRef.current = '';
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
  }, [ws.lastMessage, playAudio]);

  const handleStartConversation = useCallback(async () => {
    await media.startMedia();
    setConversationActive(true);
  }, [media]);

  const handleStopConversation = useCallback(() => {
    media.stopMedia();
    stopPlayback();
    setConversationActive(false);
    setChatMessages([]);
    setTotalFrames(0);
    setTotalAudioMs(0);
    llmBufferRef.current = '';
  }, [media, stopPlayback]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>OmniSight</h1>
        <span className="app-subtitle">AI Visual Conversation Assistant</span>
      </header>

      <main className="app-main">
        <div className="layout-top">
          <VideoPanel stream={media.stream} cameraEnabled={media.cameraEnabled} />
        </div>

        <div className="layout-status">
          <AudioIndicator
            isSpeaking={vad.isSpeaking}
            vadReady={vad.vadReady}
            micEnabled={media.micEnabled}
          />
          {conversationActive && (
            <span className="stats">
              Frames: {totalFrames} &middot; Audio: {(totalAudioMs / 1000).toFixed(1)}s
            </span>
          )}
          <ConnectionStatus state={ws.connectionState} />
          {media.error && <span className="media-error">{media.error}</span>}
          {vad.vadError && <span className="vad-error">VAD: {vad.vadError}</span>}
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
