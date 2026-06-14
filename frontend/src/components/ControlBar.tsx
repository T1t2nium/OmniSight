import { GlassButton } from './GlassButton';

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
      <GlassButton
        variant={conversationActive ? 'danger' : 'primary'}
        onClick={conversationActive ? onStopConversation : onStartConversation}
        aria-label={conversationActive ? 'Stop Conversation' : 'Start Conversation'}
      >
        {conversationActive ? '⏹ Stop Conversation [Esc]' : '▶ Start Conversation'}
      </GlassButton>

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
