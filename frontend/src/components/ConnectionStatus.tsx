import type { ConnectionState } from '../types';

interface ConnectionStatusProps {
  state: ConnectionState;
  /** Estimated latency in ms (PR 5). */
  latencyMs?: number;
  /** Current reconnect attempt number (PR 5). */
  reconnectAttempt?: number;
  /** Maximum reconnect attempts (PR 5). */
  maxReconnectAttempts?: number;
}

const STATUS_CONFIG: Record<ConnectionState, { color: string; label: string }> = {
  connected: { color: '#2ea043', label: 'Connected' },
  connecting: { color: '#d29922', label: 'Connecting...' },
  disconnected: { color: '#da3633', label: 'Disconnected' },
};

export function ConnectionStatus({
  state,
  latencyMs,
  reconnectAttempt,
  maxReconnectAttempts = 10,
}: ConnectionStatusProps) {
  const { color, label } = STATUS_CONFIG[state];

  // PR 5: show reconnect progress
  const displayLabel =
    state === 'disconnected' && reconnectAttempt && reconnectAttempt > 0
      ? `Reconnecting (${reconnectAttempt}/${maxReconnectAttempts})...`
      : label;

  // PR 6: latency color gradient
  const latencyClass =
    latencyMs !== undefined && latencyMs > 0
      ? latencyMs < 50
        ? 'latency-good'
        : latencyMs < 200
          ? 'latency-ok'
          : 'latency-bad'
      : '';

  return (
    <div className="connection-status" aria-live="polite">
      <span
        className={`status-dot ${state === 'connected' ? 'connected' : ''} ${state === 'connecting' ? 'connecting' : ''}`}
        style={{ backgroundColor: color }}
      />
      <span className="status-label">
        {state === 'connected' && '✓ '}
        {displayLabel}
      </span>
      {state === 'connected' && latencyMs !== undefined && latencyMs > 0 && (
        <span className={`latency-indicator ${latencyClass}`}>{latencyMs}ms</span>
      )}
    </div>
  );
}
