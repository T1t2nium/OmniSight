interface GlassButtonProps {
  variant: 'primary' | 'danger' | 'default';
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
  'aria-label': string;
  children: React.ReactNode;
}

/**
 * Glass-morphism button with backdrop-filter blur and gradient edge highlight.
 *
 * Variants:
 * - primary: green-tinted, used for "Start Conversation"
 * - danger:  red-tinted, used for "Stop Conversation"
 * - default: neutral glass, used for toggle buttons (Camera/Mic)
 *
 * The active prop applies a green accent border (for toggle-on state).
 */
export function GlassButton({
  variant = 'default',
  active = false,
  disabled = false,
  onClick,
  'aria-label': ariaLabel,
  children,
}: GlassButtonProps) {
  const classes = [
    'glass-btn',
    `glass-btn--${variant}`,
    active ? 'glass-btn--active' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className="glass-btn-wrapper">
      <button
        className={classes}
        onClick={onClick}
        disabled={disabled}
        aria-label={ariaLabel}
      >
        {children}
      </button>
    </div>
  );
}
