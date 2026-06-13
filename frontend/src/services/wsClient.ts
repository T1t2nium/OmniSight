import type { WSMessage, ConnectionState } from '../types';

type MessageHandler = (message: WSMessage) => void;
type StateChangeHandler = (state: ConnectionState) => void;
type LatencyHandler = (ms: number) => void;
type ReconnectStatusHandler = (info: { attempt: number; maxAttempts: number; delayMs: number }) => void;

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
  private _maxReconnectAttempts: number;
  private baseDelay: number;
  private maxDelay: number;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _state: ConnectionState = 'disconnected';
  private messageHandlers = new Set<MessageHandler>();
  private stateHandlers = new Set<StateChangeHandler>();
  private latencyHandlers = new Set<LatencyHandler>();
  private reconnectHandlers = new Set<ReconnectStatusHandler>();
  private destroyed = false;
  private _latencyMs = 0;

  constructor(url: string, opts: WSClientOptions = {}) {
    const { maxReconnectAttempts = 10, baseDelay = 1000, maxDelay = 30000 } = opts;
    this.url = url;
    this._maxReconnectAttempts = maxReconnectAttempts;
    this.baseDelay = baseDelay;
    this.maxDelay = maxDelay;
  }

  get state(): ConnectionState {
    return this._state;
  }

  /** Estimated one-way latency in ms (based on server message timestamp). */
  get latencyMs(): number {
    return this._latencyMs;
  }

  get reconnectAttempt(): number {
    return this.reconnectAttempts;
  }

  get maxReconnectAttempts(): number {
    return this._maxReconnectAttempts;
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
        // PR 5: estimate latency from server timestamp
        if (msg.timestamp) {
          this._latencyMs = Math.round(
            (Date.now() / 1000 - msg.timestamp) * 1000,
          );
          this.latencyHandlers.forEach((h) => h(this._latencyMs));
        }
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

  /** Register a handler for estimated latency updates (PR 5). */
  onLatencyUpdate(handler: LatencyHandler): () => void {
    this.latencyHandlers.add(handler);
    return () => {
      this.latencyHandlers.delete(handler);
    };
  }

  /** Register a handler for reconnect attempts (PR 5). */
  onReconnectStatus(handler: ReconnectStatusHandler): () => void {
    this.reconnectHandlers.add(handler);
    return () => {
      this.reconnectHandlers.delete(handler);
    };
  }

  // ---- Internal ----

  private setState(state: ConnectionState): void {
    this._state = state;
    this.stateHandlers.forEach((h) => h(state));
  }

  private scheduleReconnect(): void {
    if (this.destroyed || this.reconnectAttempts >= this._maxReconnectAttempts) return;

    const delay = Math.min(
      this.baseDelay * Math.pow(2, this.reconnectAttempts),
      this.maxDelay,
    );
    // ±25% jitter to avoid thundering herd
    const jittered = delay * (0.75 + Math.random() * 0.5);

    this.reconnectAttempts++;
    this.reconnectTimer = setTimeout(() => this.connect(), jittered);

    // PR 5: notify reconnect status
    const info = {
      attempt: this.reconnectAttempts,
      maxAttempts: this._maxReconnectAttempts,
      delayMs: Math.round(jittered),
    };
    this.reconnectHandlers.forEach((h) => h(info));
  }
}

export function createWSClient(url: string, opts?: WSClientOptions): WSClient {
  return new WSClient(url, opts);
}
