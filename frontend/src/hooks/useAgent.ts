import { useState, useEffect, useCallback, useRef } from 'react';
import type { WSMessage, AgentInfo, AgentSelectPayload } from '../types';

export interface UseAgentReturn {
  /** Available agents from the server. */
  agents: AgentInfo[];
  /** Currently selected agent id. */
  selectedAgentId: string;
  /** Select an agent — sends agent_select message. */
  selectAgent: (agentId: string) => void;
}

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
            return exists ? prev : payload.agents[0].agent_id;
          });
        }
      }
    });
  }, [onMessage]);

  const selectAgent = useCallback(
    (agentId: string) => {
      setSelectedAgentId(agentId);
      const payload: AgentSelectPayload = { agent_id: agentId };
      send({
        type: 'agent_select',
        session_id: sessionIdRef.current,
        timestamp: Date.now() / 1000,
        payload: payload as unknown as Record<string, unknown>,
      });
    },
    [send],
  );

  return { agents, selectedAgentId, selectAgent };
}
