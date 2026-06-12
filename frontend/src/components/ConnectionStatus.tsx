import type { ConnectionState } from '../types';

interface ConnectionStatusProps {
  state: ConnectionState;
}

const STATUS_CONFIG: Record<ConnectionState, { color: string; label: string }> = {
  connected: { color: '#2ea043', label: 'Connected' },
  connecting: { color: '#d29922', label: 'Connecting...' },
  disconnected: { color: '#da3633', label: 'Disconnected' },
};

export function ConnectionStatus({ state }: ConnectionStatusProps) {
  const { color, label } = STATUS_CONFIG[state];

  return (
    <div className="connection-status">
      <span className="status-dot" style={{ backgroundColor: color }} />
      <span className="status-label">{label}</span>
    </div>
  );
}
