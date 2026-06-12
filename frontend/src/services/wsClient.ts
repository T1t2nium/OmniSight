import type { WSMessage, ConnectionState } from '../types';

type MessageHandler = (message: WSMessage) => void;
type StateChangeHandler = (state: ConnectionState) => void;

export interface WSClientOptions {
  maxReconnectAttempts?: number;
  baseDelay?: number;
  maxDelay?: number;
}

/**
 * Thin WebSocket wrapper with automatic reconnection and event-based dispatch.
 *
 * Usage:
 *   const client = createWSClient('ws://localhost:8000/ws');
 *   client.onMessage(msg => console.log(msg));
 *   client.connect();
 *   client.send({ type: 'vad_event', session_id: '...', timestamp: 0, payload: {} });
 */
export class WSClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts: number;
  private baseDelay: number;
  private maxDelay: number;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _state: ConnectionState = 'disconnected';
  private messageHandlers = new Set<MessageHandler>();
  private stateHandlers = new Set<StateChangeHandler>();
  private destroyed = false;

  constructor(url: string, opts: WSClientOptions = {}) {
    const { maxReconnectAttempts = 10, baseDelay = 1000, maxDelay = 30000 } = opts;
    this.url = url;
    this.maxReconnectAttempts = maxReconnectAttempts;
    this.baseDelay = baseDelay;
    this.maxDelay = maxDelay;
  }

  get state(): ConnectionState {
    return this._state;
  }

  // ---- Public API ----

  connect(): void {
    if (this.destroyed) return;
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING)
      return;

    this.setState('connecting');

    try {
      this.ws = new WebSocket(this.url);
    } catch {
      this.setState('disconnected');
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.setState('connected');
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string) as WSMessage;
        this.messageHandlers.forEach((h) => h(msg));
      } catch {
        // Ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      if (!this.destroyed) {
        this.setState('disconnected');
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      // onclose fires after onerror; reconnect is handled there
    };
  }

  disconnect(): void {
    this.destroyed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
    this.setState('disconnected');
  }

  send(message: WSMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  /** Register a handler for every incoming WSMessage. Returns an unsubscribe function. */
  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => {
      this.messageHandlers.delete(handler);
    };
  }

  /** Register a handler for connection state changes. Returns an unsubscribe function. */
  onStateChange(handler: StateChangeHandler): () => void {
    // Immediately notify of current state
    handler(this._state);
    this.stateHandlers.add(handler);
    return () => {
      this.stateHandlers.delete(handler);
    };
  }

  // ---- Internal ----

  private setState(state: ConnectionState): void {
    this._state = state;
    this.stateHandlers.forEach((h) => h(state));
  }

  private scheduleReconnect(): void {
    if (this.destroyed || this.reconnectAttempts >= this.maxReconnectAttempts) return;

    const delay = Math.min(
      this.baseDelay * Math.pow(2, this.reconnectAttempts),
      this.maxDelay,
    );
    // ±25% jitter to avoid thundering herd
    const jittered = delay * (0.75 + Math.random() * 0.5);

    this.reconnectAttempts++;
    this.reconnectTimer = setTimeout(() => this.connect(), jittered);
  }
}

export function createWSClient(url: string, opts?: WSClientOptions): WSClient {
  return new WSClient(url, opts);
}
