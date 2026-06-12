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

  if (aiSpeaking) {
    ringClass = 'indicator-ring ai-speaking';
    label = 'AI Speaking...';
  } else if (isSpeaking) {
    ringClass = 'indicator-ring speaking';
    label = 'Speaking...';
  } else if (vadReady) {
    ringClass = 'indicator-ring listening';
    label = 'Listening...';
  } else {
    ringClass = 'indicator-ring listening';
    label = 'VAD loading...';
  }

  return (
    <div className="audio-indicator">
      <div className={ringClass} />
      <span className="indicator-label">{label}</span>
    </div>
  );
}
