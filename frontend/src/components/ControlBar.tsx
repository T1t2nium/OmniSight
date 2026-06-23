import { GlassButton } from './GlassButton';

interface ControlBarProps {
  conversationActive: boolean;
  cameraEnabled: boolean;
  micEnabled: boolean;
  onStartConversation: () => void;
  onStopConversation: () => void;
  onToggleCamera: () => void;
  onToggleMic: () => void;
  startDisabled?: boolean;
  startHint?: string;
}

export function ControlBar({
  conversationActive,
  cameraEnabled,
  micEnabled,
  onStartConversation,
  onStopConversation,
  onToggleCamera,
  onToggleMic,
  startDisabled = false,
  startHint = '',
}: ControlBarProps) {
  return (
    <div className="control-bar">
      <div className="control-bar__start-group">
        <GlassButton
          variant={conversationActive ? 'danger' : 'primary'}
          onClick={conversationActive ? onStopConversation : onStartConversation}
          disabled={!conversationActive && startDisabled}
          aria-label={conversationActive ? 'Stop Conversation' : startDisabled ? startHint : 'Start Conversation'}
        >
          {conversationActive ? '⏹ Stop Conversation [Esc]' : '▶ Start Conversation'}
        </GlassButton>
        {!conversationActive && startHint && (
          <span className="control-bar__hint">{startHint}</span>
        )}
      </div>

      <GlassButton
        variant="default"
        active={cameraEnabled}
        onClick={onToggleCamera}
        disabled={!conversationActive}
        aria-label={cameraEnabled ? 'Turn Camera Off' : 'Turn Camera On'}
      >
        {cameraEnabled ? '📷 Camera On' : '📷 Camera Off'}
      </GlassButton>

      <GlassButton
        variant="default"
        active={micEnabled}
        onClick={onToggleMic}
        disabled={!conversationActive}
        aria-label={micEnabled ? 'Mute Microphone' : 'Unmute Microphone'}
      >
        {micEnabled ? '🎤 Mic On [Space]' : '🎤 Mic Off [Space]'}
      </GlassButton>
    </div>
  );
}
