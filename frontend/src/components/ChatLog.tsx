import { useRef, useEffect } from 'react';
import type { WSMessage, TranscriptPayload, LLMResponsePayload, AIStatusPayload, ErrorPayload } from '../types';

interface ChatLogProps {
  messages: WSMessage[];
}

function BubbledMessage({ msg }: { msg: WSMessage }) {
  switch (msg.type) {
    // PR 4: tts_audio and interrupt are handled by audio player, not displayed
    case 'tts_audio':
    case 'interrupt':
      return null;

    case 'transcript': {
      const p = msg.payload as unknown as TranscriptPayload;
      return (
        <div className="chat-bubble-row user">
          <div className="chat-bubble-avatar user" aria-hidden="true">👤</div>
          <div className="chat-bubble chat-bubble-user">
            <div className="chat-bubble-label">You</div>
            <div className="chat-bubble-text">{p.text}</div>
            {p.language && (
              <div className="chat-bubble-meta">
                {p.language} &middot; {(p.duration_ms / 1000).toFixed(1)}s
              </div>
            )}
          </div>
        </div>
      );
    }

    case 'llm_response': {
      const p = msg.payload as unknown as LLMResponsePayload;
      if (p.done) {
        return (
          <div className="chat-bubble-row">
            <div className="chat-bubble-avatar ai" aria-hidden="true">◈</div>
            <div className="chat-bubble chat-bubble-ai">
              <div className="chat-bubble-label">AI</div>
              <div className="chat-bubble-text">{p.delta}</div>
              {p.total_duration > 0 && (
                <div className="chat-bubble-meta">
                  {(p.total_duration * 1000).toFixed(0)}ms
                </div>
              )}
            </div>
          </div>
        );
      }
      // Streaming delta
      return (
        <div className="chat-bubble-row">
          <div className="chat-bubble-avatar ai" aria-hidden="true">◈</div>
          <div className="chat-bubble chat-bubble-ai chat-bubble-streaming">
            <div className="chat-bubble-label">AI</div>
            <div className="chat-bubble-text">
              {p.delta || '...'}
              <span className="streaming-cursor" />
            </div>
          </div>
        </div>
      );
    }

    case 'ai_status': {
      const p = msg.payload as unknown as AIStatusPayload;
      if (p.status === 'idle') return null;
      return (
        <div className={`chat-ai-status chat-ai-status-${p.status}`}>
          {p.status === 'thinking' && 'AI is thinking...'}
        </div>
      );
    }

    case 'error': {
      const p = msg.payload as unknown as ErrorPayload;
      return <div className="chat-error-msg">⚠ {p.message}</div>;
    }

    case 'server_status':
    case 'echo':
      return (
        <>
          <span className="msg-type">{msg.type}</span>
          <pre className="msg-payload">
            {JSON.stringify(msg.payload, null, 2)}
          </pre>
        </>
      );

    default:
      return (
        <>
          <span className="msg-type">{msg.type}</span>
          <pre className="msg-payload">
            {JSON.stringify(msg.payload, null, 2)}
          </pre>
        </>
      );
  }
}

export function ChatLog({ messages }: ChatLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="chat-log" role="log" aria-live="polite" aria-label="Conversation messages">
      {messages.length === 0 && (
        <div className="chat-empty">
          <div className="chat-empty-icon" aria-hidden="true">💬</div>
          <h3>Start a Conversation</h3>
          <p>Click the green button below to begin. Your camera and microphone will be activated.</p>
          <div className="chat-empty-hints">
            <span className="chat-empty-hint">🎤 Speak naturally</span>
            <span className="chat-empty-hint">📷 AI sees your camera</span>
            <span className="chat-empty-hint">Space = Toggle Mic</span>
            <span className="chat-empty-hint">Esc = Interrupt</span>
          </div>
        </div>
      )}
      {messages.map((msg, i) => {
        const rendered = <BubbledMessage msg={msg} />;
        if (!rendered) return null;
        return (
          <div key={i} className={`chat-message chat-${msg.type}`}>
            {rendered}
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
