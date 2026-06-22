import type { AgentInfo } from '../types';

interface AgentSelectorProps {
  agents: AgentInfo[];
  selectedAgentId: string;
  onSelect: (agentId: string) => void;
}

/**
 * Agent selector — glass-morphism capsule tags.
 *
 * Displays available agents as selectable pill-shaped labels.
 * When only one agent exists, it appears as a static label
 * showing the active persona.
 */
export function AgentSelector({
  agents,
  selectedAgentId,
  onSelect,
}: AgentSelectorProps) {
  if (agents.length === 0) return null;

  const selected = agents.find((a) => a.agent_id === selectedAgentId);
  const label = selected
    ? `${selected.name}`
    : '选择 Agent';

  return (
    <div className="agent-selector" role="radiogroup" aria-label="选择 Agent">
      {agents.length === 1 ? (
        <span className="agent-selector__label" title={selected?.description}>
          💬 {label}
        </span>
      ) : (
        agents.map((agent) => (
          <button
            key={agent.agent_id}
            className={`agent-selector__chip${agent.agent_id === selectedAgentId ? ' agent-selector__chip--active' : ''}`}
            role="radio"
            aria-checked={agent.agent_id === selectedAgentId}
            onClick={() => onSelect(agent.agent_id)}
            title={agent.description}
          >
            {agent.name}
          </button>
        ))
      )}
    </div>
  );
}
