import { useRef, useEffect } from 'react';
import type { WSMessage } from '../types';

interface ChatLogProps {
  messages: WSMessage[];
}

export function ChatLog({ messages }: ChatLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="chat-log">
      {messages.length === 0 && (
        <div className="chat-empty">
          Start a conversation to see messages here...
        </div>
      )}
      {messages.map((msg, i) => (
        <div key={i} className={`chat-message chat-${msg.type}`}>
          <span className="msg-type">{msg.type}</span>
          <pre className="msg-payload">
            {JSON.stringify(msg.payload, null, 2)}
          </pre>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
