interface AudioIndicatorProps {
  isSpeaking: boolean; // User is speaking (VAD detected)
  vadReady: boolean;
  micEnabled: boolean;
  aiSpeaking?: boolean; // PR 4: AI is speaking via TTS
}

export function AudioIndicator({
  isSpeaking,
  vadReady,
  micEnabled,
  aiSpeaking = false,
}: AudioIndicatorProps) {
  if (!micEnabled) return null;

  let ringClass: string;
  let label: string;
  let ariaLabel: string;

  if (aiSpeaking) {
    ringClass = 'indicator-ring ai-speaking';
    label = 'AI Speaking...';
    ariaLabel = 'Voice activity: AI is speaking';
  } else if (isSpeaking) {
    ringClass = 'indicator-ring speaking';
    label = 'Speaking...';
    ariaLabel = 'Voice activity: user is speaking';
  } else if (vadReady) {
    ringClass = 'indicator-ring listening';
    label = 'Listening...';
    ariaLabel = 'Voice activity: listening for speech';
  } else {
    ringClass = 'indicator-ring listening';
    label = 'VAD loading...';
    ariaLabel = 'Voice activity: loading voice detection';
  }

  return (
    <div className="audio-indicator" role="status" aria-label={ariaLabel}>
      <div className={ringClass} aria-hidden="true" />
      <span className="indicator-label">{label}</span>
    </div>
  );
}
