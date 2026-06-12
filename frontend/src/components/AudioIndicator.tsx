interface AudioIndicatorProps {
  isSpeaking: boolean;
  vadReady: boolean;
  micEnabled: boolean;
}

export function AudioIndicator({ isSpeaking, vadReady, micEnabled }: AudioIndicatorProps) {
  if (!micEnabled) return null;

  const ringClass = isSpeaking ? 'indicator-ring speaking' : 'indicator-ring listening';
  const label = isSpeaking ? 'Speaking...' : vadReady ? 'Listening...' : 'VAD loading...';

  return (
    <div className="audio-indicator">
      <div className={ringClass} />
      <span className="indicator-label">{label}</span>
    </div>
  );
}
