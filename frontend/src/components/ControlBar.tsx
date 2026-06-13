interface ControlBarProps {
  conversationActive: boolean;
  cameraEnabled: boolean;
  micEnabled: boolean;
  onStartConversation: () => void;
  onStopConversation: () => void;
  onToggleCamera: () => void;
  onToggleMic: () => void;
}

export function ControlBar({
  conversationActive,
  cameraEnabled,
  micEnabled,
  onStartConversation,
  onStopConversation,
  onToggleCamera,
  onToggleMic,
}: ControlBarProps) {
  return (
    <div className="control-bar">
      <button
        className={`btn ${conversationActive ? 'btn-stop' : 'btn-start'}`}
        onClick={conversationActive ? onStopConversation : onStartConversation}
      >
        {conversationActive ? '⏹ Stop Conversation [Esc]' : '▶ Start Conversation'}
      </button>

      <button
        className={`btn ${cameraEnabled ? 'btn-active' : 'btn-inactive'}`}
        onClick={onToggleCamera}
        disabled={!conversationActive}
      >
        {cameraEnabled ? '📷 Camera On' : '📷 Camera Off'}
      </button>

      <button
        className={`btn ${micEnabled ? 'btn-active' : 'btn-inactive'}`}
        onClick={onToggleMic}
        disabled={!conversationActive}
      >
        {micEnabled ? '🎤 Mic On [Space]' : '🎤 Mic Off [Space]'}
      </button>
    </div>
  );
}
