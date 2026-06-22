import { useState, useRef, useEffect } from 'react';
import type { AgentInfo } from '../types';

interface AgentSelectorProps {
  agents: AgentInfo[];
  selectedAgentId: string;
  onSelect: (agentId: string) => void;
}

/**
 * Agent selector — glass-morphism dropdown.
 *
 * Compact dropdown that shows the current agent and expands
 * to reveal all available agents on click. Replaces the old
 * pill-button layout for a cleaner header.
 */
export function AgentSelector({
  agents,
  selectedAgentId,
  onSelect,
}: AgentSelectorProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const selected = agents.find((a) => a.agent_id === selectedAgentId);
  const displayName = selected ? selected.name : '选择 Agent';

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  if (agents.length === 0) return null;

  return (
    <div className="agent-selector" ref={ref}>
      <button
        className="agent-selector__trigger"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="agent-selector__current">{displayName}</span>
        <span className={`agent-selector__arrow ${open ? 'agent-selector__arrow--open' : ''}`}>
          ▾
        </span>
      </button>

      {open && (
        <div className="agent-selector__menu" role="listbox">
          {agents.map((agent) => (
            <button
              key={agent.agent_id}
              className={`agent-selector__option${
                agent.agent_id === selectedAgentId ? ' agent-selector__option--active' : ''
              }`}
              role="option"
              aria-selected={agent.agent_id === selectedAgentId}
              onClick={() => {
                onSelect(agent.agent_id);
                setOpen(false);
              }}
            >
              <span className="agent-selector__option-name">{agent.name}</span>
              <span className="agent-selector__option-desc">{agent.description}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
