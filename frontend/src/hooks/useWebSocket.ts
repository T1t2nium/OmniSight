import { useEffect, useState, useRef, useCallback } from 'react';
import { createWSClient, type WSClient } from '../services/wsClient';
import type { WSMessage, ConnectionState } from '../types';

/** WebSocket URL — uses Vite proxy in dev, same-origin in production. */
const WS_URL = `ws://${window.location.host}/ws`;

export interface UseWebSocketReturn {
  connectionState: ConnectionState;
  lastMessage: WSMessage | null;
  /** Estimated one-way latency in ms (PR 5). */
  latencyMs: number;
  /** Current reconnect attempt number (0 if connected, PR 5). */
  reconnectAttempt: number;
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
  const [latencyMs, setLatencyMs] = useState(0);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const clientRef = useRef<WSClient | null>(null);
  const handlersRef = useRef<Set<(msg: WSMessage) => void>>(new Set());
  // Track sessionId to avoid re-running effect unnecessarily
  const sessionRef = useRef(sessionId);

  useEffect(() => {
    sessionRef.current = sessionId;
    const client = createWSClient(WS_URL);
    clientRef.current = client;

    const unsubState = client.onStateChange((state) => {
      setConnectionState(state);
      // Reset reconnect counter when connected
      if (state === 'connected') {
        setReconnectAttempt(0);
      }
    });
    const unsubMsg = client.onMessage((msg) => {
      setLastMessage(msg);
      handlersRef.current.forEach((h) => h(msg));
    });
    const unsubLatency = client.onLatencyUpdate(setLatencyMs);
    const unsubReconnect = client.onReconnectStatus((info) => {
      setReconnectAttempt(info.attempt);
    });

    client.connect();

    return () => {
      unsubState();
      unsubMsg();
      unsubLatency();
      unsubReconnect();
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

  return { connectionState, lastMessage, latencyMs, reconnectAttempt, send, onMessage };
}
