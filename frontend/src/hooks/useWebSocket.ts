import { useEffect, useState, useRef, useCallback } from 'react';
import { createWSClient, type WSClient } from '../services/wsClient';
import type { WSMessage, ConnectionState } from '../types';

/** WebSocket URL — uses Vite proxy in dev, same-origin in production. */
const WS_URL = `ws://${window.location.host}/ws`;

export interface UseWebSocketReturn {
  connectionState: ConnectionState;
  lastMessage: WSMessage | null;
  send: (message: WSMessage) => void;
  onMessage: (handler: (msg: WSMessage) => void) => () => void;
}

/**
 * Manages a single WebSocket connection lifecycle.
 * Auto-connects on mount, auto-disconnects on unmount.
 *
 * @param sessionId - Stable UUID that identifies this client session
 */
export function useWebSocket(sessionId: string): UseWebSocketReturn {
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const clientRef = useRef<WSClient | null>(null);
  const handlersRef = useRef<Set<(msg: WSMessage) => void>>(new Set());
  // Track sessionId to avoid re-running effect unnecessarily
  const sessionRef = useRef(sessionId);

  useEffect(() => {
    sessionRef.current = sessionId;
    const client = createWSClient(WS_URL);
    clientRef.current = client;

    const unsubState = client.onStateChange(setConnectionState);
    const unsubMsg = client.onMessage((msg) => {
      setLastMessage(msg);
      handlersRef.current.forEach((h) => h(msg));
    });

    client.connect();

    return () => {
      unsubState();
      unsubMsg();
      client.disconnect();
      clientRef.current = null;
    };
    // sessionId is intentionally omitted — reconnects only on explicit unmount/mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const send = useCallback((message: WSMessage) => {
    clientRef.current?.send(message);
  }, []);

  const onMessage = useCallback(
    (handler: (msg: WSMessage) => void): (() => void) => {
      handlersRef.current.add(handler);
      return () => {
        handlersRef.current.delete(handler);
      };
    },
    [],
  );

  return { connectionState, lastMessage, send, onMessage };
}
