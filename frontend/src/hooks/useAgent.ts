import { useState, useEffect, useCallback, useRef } from 'react';
import type { WSMessage, AgentInfo, AgentUIConfig, AgentSelectPayload } from '../types';

export interface UseAgentReturn {
  /** Available agents from the server. */
  agents: AgentInfo[];
  /** Currently selected agent id. */
  selectedAgentId: string;
  /** UI config for the currently selected agent. */
  uiConfig: AgentUIConfig;
  /** Select an agent — sends agent_select message. */
  selectAgent: (agentId: string) => void;
}

const DEFAULT_UI_CONFIG: AgentUIConfig = {
  show_document_upload: false,
  show_question_bank: false,
  header_color: '#6366f1',
};

/**
 * Manages agent selection state — listens for agent_list messages
 * and provides a selectAgent function that sends agent_select.
 *
 * @param send - WebSocket send function (from useWebSocket)
 * @param onMessage - WebSocket message listener (from useWebSocket)
 * @param sessionId - Current session UUID
 */
export function useAgent(
  send: (msg: WSMessage) => void,
  onMessage: (handler: (msg: WSMessage) => void) => () => void,
  sessionId: string,
): UseAgentReturn {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('chat');
  const [uiConfig, setUiConfig] = useState<AgentUIConfig>(DEFAULT_UI_CONFIG);
  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;

  // Listen for agent_list messages from the server
  useEffect(() => {
    return onMessage((msg: WSMessage) => {
      if (msg.type === 'agent_list') {
        const payload = msg.payload as unknown as { agents: AgentInfo[] };
        if (payload.agents && payload.agents.length > 0) {
          setAgents(payload.agents);
          // Default to first agent if not already set
          setSelectedAgentId((prev) => {
            const exists = payload.agents.some((a) => a.agent_id === prev);
            if (exists) {
              // Update ui_config for the currently selected agent
              const current = payload.agents.find((a) => a.agent_id === prev);
              if (current?.ui_config) setUiConfig(current.ui_config);
              return prev;
            }
            const first = payload.agents[0];
            if (first.ui_config) setUiConfig(first.ui_config);
            return first.agent_id;
          });
        }
      }
    });
  }, [onMessage]);

  const selectAgent = useCallback(
    (agentId: string) => {
      setSelectedAgentId(agentId);
      // Update ui_config for selected agent
      const agent = agents.find((a) => a.agent_id === agentId);
      if (agent?.ui_config) setUiConfig(agent.ui_config);
      else setUiConfig(DEFAULT_UI_CONFIG);

      const payload: AgentSelectPayload = { agent_id: agentId };
      send({
        type: 'agent_select',
        session_id: sessionIdRef.current,
        timestamp: Date.now() / 1000,
        payload: payload as unknown as Record<string, unknown>,
      });
    },
    [send, agents],
  );

  return { agents, selectedAgentId, uiConfig, selectAgent };
}
