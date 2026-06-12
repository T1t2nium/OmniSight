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
import type { WSMessage } from './types';

/** Mute repetitive echo types (fired at high frequency). */
const MUTED_ECHO_TYPES = new Set(['video_frame']);

function App() {
  const [conversationActive, setConversationActive] = useState(false);
  const [chatMessages, setChatMessages] = useState<WSMessage[]>([]);
  const [totalFrames, setTotalFrames] = useState(0);
  const [totalAudioMs, setTotalAudioMs] = useState(0);
  const sessionIdRef = useRef<string>(crypto.randomUUID());

  const media = useMediaStream();
  const ws = useWebSocket(sessionIdRef.current);
  const vad = useVAD({
    stream: media.stream,
    sessionId: sessionIdRef.current,
    sendMessage: ws.send,
    enabled: conversationActive && media.micEnabled,
  });
  void useAudioPlayer(); // Placeholder — PR 3 implements actual playback

  // Periodic video frame capture (4 FPS JPEG via WebSocket)
  useFrameCapture({
    stream: media.stream,
    sessionId: sessionIdRef.current,
    sendMessage: ws.send,
    enabled: conversationActive && media.cameraEnabled,
  });

  // Process incoming messages: update stats, filter muted echoes from chat log
  useEffect(() => {
    const msg = ws.lastMessage;
    if (!msg) return;

    // Extract stats from echo payloads
    if (msg.type === 'echo') {
      const p = msg.payload as Record<string, unknown>;
      if (typeof p.total_frames === 'number') setTotalFrames(p.total_frames);
      if (typeof p.total_audio_ms === 'number') setTotalAudioMs(p.total_audio_ms);

      // Skip high-frequency echoes that would spam the log
      if (typeof p.received_type === 'string' && MUTED_ECHO_TYPES.has(p.received_type)) {
        return;
      }
    }

    setChatMessages((prev) => [...prev, msg]);
  }, [ws.lastMessage]);

  const handleStartConversation = useCallback(async () => {
    await media.startMedia();
    setConversationActive(true);
  }, [media]);

  const handleStopConversation = useCallback(() => {
    media.stopMedia();
    setConversationActive(false);
    setChatMessages([]);
    setTotalFrames(0);
    setTotalAudioMs(0);
  }, [media]);

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
