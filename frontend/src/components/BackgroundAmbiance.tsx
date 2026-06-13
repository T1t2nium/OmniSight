import { useEffect, useRef } from 'react';

export type AmbianceState = 'idle' | 'user-speaking' | 'ai-speaking';

interface BackgroundAmbianceProps {
  state: AmbianceState;
  enabled: boolean;
}

/** Maps ambiance state to CSS custom property values for the light color. */
const STATE_COLORS: Record<AmbianceState, string> = {
  idle: '126, 184, 255',       // soft teal-blue
  'user-speaking': '251, 191, 36',  // warm amber-gold
  'ai-speaking': '167, 139, 250',   // soft purple-lavender
};

/**
 * Full-viewport background light source that breathes and changes color
 * based on conversation state (idle → user speaking → AI responding).
 *
 * Pure visual — zero impact on layout or interaction.
 */
export function BackgroundAmbiance({ state, enabled }: BackgroundAmbianceProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const prevStateRef = useRef<AmbianceState>('idle');

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;

    // When state changes, briefly intensify the light for a "pulse" effect
    if (prevStateRef.current !== state) {
      el.style.transition = 'opacity 0.6s ease';
      el.style.opacity = '1';
      setTimeout(() => {
        el.style.opacity = '';
      }, 600);
    }
    prevStateRef.current = state;

    // Drive color via CSS custom property
    const color = STATE_COLORS[state];
    document.documentElement.style.setProperty('--ambiance-rgb', color);
  }, [state]);

  // Clean up CSS variable on unmount
  useEffect(() => {
    return () => {
      document.documentElement.style.removeProperty('--ambiance-rgb');
    };
  }, []);

  if (!enabled) return null;

  return (
    <div
      ref={rootRef}
      className="bg-ambiance"
      aria-hidden="true"
      data-state={state}
    />
  );
}
