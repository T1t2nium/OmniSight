import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { VideoPanel } from './components/VideoPanel';
import { AudioIndicator } from './components/AudioIndicator';
import { ConnectionStatus } from './components/ConnectionStatus';
import { ControlBar } from './components/ControlBar';
import { ChatLog } from './components/ChatLog';
import { AgentSelector } from './components/AgentSelector';
import { DocumentUpload } from './components/DocumentUpload';
import type { UploadZoneState } from './components/DocumentUpload';
import { QuestionBank } from './components/QuestionBank';
import NeuralBackground from './components/NeuralBackground';
import { useWebSocket } from './hooks/useWebSocket';
import { useMediaStream } from './hooks/useMediaStream';
import { useVAD } from './hooks/useVAD';
import { useAudioPlayer } from './hooks/useAudioPlayer';
import { useFrameCapture } from './hooks/useFrameCapture';
import { useAgent } from './hooks/useAgent';
import type {
  WSMessage,
  LLMResponsePayload,
  TTSAudioPayload,
  InterruptPayload,
  DocumentParsedPayload,
  QuestionBankPayload,
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
  // PR 4: tracks expected TTS provider for the current pipeline ('piper' | 'browser')
  const ttsProviderRef = useRef<string>('browser');

  const media = useMediaStream();
  const ws = useWebSocket(sessionIdRef.current);
  const {
    playPCM16,
    playSpeechSynthesis,
    stopPlayback,
    isSpeaking: aiSpeaking,
  } = useAudioPlayer();
  // PR 5: refs for latest state (used in keyboard handler to avoid stale closures)
  const conversationActiveRef = useRef(conversationActive);
  conversationActiveRef.current = conversationActive;
  const aiSpeakingRef = useRef(aiSpeaking);
  aiSpeakingRef.current = aiSpeaking;
  const vad = useVAD({
    stream: media.vadStream,
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

  // PR 11: Agent selection
  const agent = useAgent(ws.send, ws.onMessage, sessionIdRef.current);

  // PR 13: Document upload state (lifted to App for server response handling)
  const [jdZone, setJdZone] = useState<UploadZoneState>({
    status: 'idle', filename: '', error: '',
  });
  const [resumeZone, setResumeZone] = useState<UploadZoneState>({
    status: 'idle', filename: '', error: '',
  });
  const [questionBank, setQuestionBank] = useState<QuestionBankPayload | null>(null);

  // ---- Background ambiance: particle color follows conversation state ----
  const ambianceColor = useMemo(() => {
    if (!conversationActive) return '#6366f1';  // indigo
    if (vad.isSpeaking) return '#fbbf24';        // amber-gold
    if (aiSpeaking) return '#a78bfa';            // purple
    return '#6366f1';                            // indigo
  }, [conversationActive, vad.isSpeaking, aiSpeaking]);

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

      // ---- PR 4: TTS provider announced at pipeline start ----
      if (msg.type === 'tts_info') {
        const p = msg.payload as unknown as { provider: string };
        ttsProviderRef.current = p.provider || 'browser';
        return;
      }

      // ---- PR 4: TTS Audio playback ----
      if (msg.type === 'tts_audio') {
        const p = msg.payload as unknown as TTSAudioPayload;
        playPCM16Ref.current(p.data, p.sample_rate, p.text);
        return;
      }

      // ---- PR 4: Interrupt (server confirmed barge-in) ----
      if (msg.type === 'interrupt') {
        console.log('[App] Interrupt received:', (msg.payload as unknown as InterruptPayload).reason);
        stopPlaybackRef.current();
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

      // ---- New transcript: user spoke → append to chat ----
      if (msg.type === 'transcript') {
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
        // Final chunk — update existing streaming message, or append new
        const finalText = llmBufferRef.current || p.delta;
        if (!finalText) return;
        const finalDuration = p.total_duration;
        llmBufferRef.current = '';

        // PR 4: SpeechSynthesis only when backend explicitly says 'browser'.
        // When Piper is active, the backend sends tts_audio separately.
        if (ttsProviderRef.current === 'browser') {
          playSpeechSynthesisRef.current(finalText);
        }

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

      // ---- PR 13: Document parsed response ----
      if (msg.type === 'document_parsed') {
        const p = msg.payload as unknown as DocumentParsedPayload;
        if (p.doc_type === 'jd') {
          setJdZone((prev) => ({ ...prev, status: 'done', filename: p.filename || prev.filename, error: '' }));
        } else {
          setResumeZone((prev) => ({ ...prev, status: 'done', filename: p.filename || prev.filename, error: '' }));
        }
        return;
      }

      // ---- PR 13: Question bank received ----
      if (msg.type === 'question_bank') {
        const p = msg.payload as unknown as QuestionBankPayload;
        setQuestionBank(p);
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
    ttsProviderRef.current = 'browser';
    // PR 13: Reset interview state
    setJdZone({ status: 'idle', filename: '', error: '' });
    setResumeZone({ status: 'idle', filename: '', error: '' });
    setQuestionBank(null);
  }, [media]);

  // PR 13: Handle document upload start
  const handleUploadStart = useCallback((docType: 'jd' | 'resume', filename: string) => {
    const setter = docType === 'jd' ? setJdZone : setResumeZone;
    if (!filename) {
      setter({ status: 'error', filename: '', error: '仅支持 PDF 和 DOCX 文件' });
    } else {
      setter({ status: 'uploading', filename, error: '' });
    }
  }, []);

  // ---- PR 5: Keyboard shortcuts ----
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore when user is typing in an input or textarea
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      // Space: toggle microphone
      if (e.code === 'Space') {
        e.preventDefault();
        if (conversationActiveRef.current) {
          media.toggleMic();
        }
        return;
      }

      // Escape: interrupt AI speech, or stop conversation if idle
      if (e.code === 'Escape') {
        e.preventDefault();
        if (aiSpeakingRef.current) {
          // Barge-in: stop audio + notify backend
          stopPlaybackRef.current();
          ws.send({
            type: 'vad_event',
            session_id: sessionIdRef.current,
            timestamp: Date.now() / 1000,
            payload: { event: 'speech_start' },
          });
        } else if (conversationActiveRef.current) {
          handleStopConversation();
        }
        return;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [media.toggleMic, ws.send, handleStopConversation]);

  return (
    <>
      <NeuralBackground
        color={ambianceColor}
        trailOpacity={0.12}
        speed={0.8}
      />
      <div className="app">
        <header className="app-header">
        <div className="app-logo" aria-hidden="true">◈</div>
        <h1>OmniSight</h1>
        <span className="app-subtitle">AI Vision</span>
        <div className="app-header__agent">
          <AgentSelector
            agents={agent.agents}
            selectedAgentId={agent.selectedAgentId}
            onSelect={agent.selectAgent}
          />
        </div>
      </header>

      <main className="app-main">
        <div className="layout-top">
          <div className="layout-top__video">
            <VideoPanel
              stream={media.stream}
              cameraEnabled={media.cameraEnabled}
              streamVersion={media.streamVersion}
            />
          </div>
          <div
            className={`layout-top__side${
              agent.uiConfig.show_document_upload ? ' layout-top__side--open' : ''
            }`}
          >
            <DocumentUpload
              send={ws.send}
              sessionId={sessionIdRef.current}
              visible={agent.uiConfig.show_document_upload}
              jdZone={jdZone}
              resumeZone={resumeZone}
              onUploadStart={handleUploadStart}
            />
          </div>
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
          <ConnectionStatus
            state={ws.connectionState}
            latencyMs={ws.latencyMs}
            reconnectAttempt={ws.reconnectAttempt}
          />
          {media.error && <span className="media-error">{media.error}</span>}
          {vad.vadError && (
            <span className="vad-error">VAD: {vad.vadError}</span>
          )}
        </div>

        <QuestionBank
          bank={questionBank}
          visible={agent.uiConfig.show_question_bank}
        />

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
    </>
  );
}

export default App;
