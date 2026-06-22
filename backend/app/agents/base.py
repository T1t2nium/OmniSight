"""BaseAgent ABC + AgentRegistry — extensible Agent framework.

Each Agent defines its own system_prompt so the AI behaves differently
for different scenarios (visual chat companion, interview assistant, etc.).

Usage:
    from app.agents.base import AgentRegistry, BaseAgent, ChatAgent

    # Register agents at startup (main.py lifespan)
    AgentRegistry.register(ChatAgent())

    # Look up agent by id (ws.py pipeline)
    agent = AgentRegistry.get("chat")
    system_prompt = agent.system_prompt if agent else SYSTEM_PROMPT
"""

from abc import ABC, abstractmethod

from app.services.prompts import SYSTEM_PROMPT

# Well-known agent IDs
CHAT_AGENT_ID = "chat"


class BaseAgent(ABC):
    """Abstract base for all OmniSight agents.

    Each agent provides a system prompt that shapes the AI's persona
    and behavior for a specific scenario.
    """

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Unique agent identifier (e.g. 'chat', 'interview')."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable display name (e.g. '视觉聊天伴侣')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """One-line description shown in the agent selector."""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The system prompt injected into every AI call for this agent."""
        ...

    def get_ui_config(self) -> dict:
        """Frontend UI hints — component visibility, layout options, etc.

        Override in subclasses to show/hide UI elements:
            {
                "show_document_upload": False,  # PR 12: InterviewAgent → True
                "show_question_bank": False,    # PR 13
                "header_color": "#6366f1",      # accent color for agent header
            }
        """
        return {}


# ---- Default Agent: Visual Chat Companion ----


class ChatAgent(BaseAgent):
    """Default visual chat companion — the original OmniSight persona."""

    @property
    def agent_id(self) -> str:
        return CHAT_AGENT_ID

    @property
    def name(self) -> str:
        return "视觉聊天伴侣"

    @property
    def description(self) -> str:
        return "具备视觉能力的AI日常对话助手，像朋友一样自然交流"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def get_ui_config(self) -> dict:
        return {
            "show_document_upload": False,
            "show_question_bank": False,
            "header_color": "#6366f1",
        }


# ---- Agent Registry ----


class AgentRegistry:
    """Class-method singleton that holds all registered agents.

    Usage:
        AgentRegistry.register(ChatAgent())
        agent = AgentRegistry.get("chat")
        agents = AgentRegistry.list_agents()
    """

    _agents: dict[str, BaseAgent] = {}

    @classmethod
    def register(cls, agent: BaseAgent) -> None:
        """Register an agent instance. Overwrites existing agent with same id."""
        cls._agents[agent.agent_id] = agent

    @classmethod
    def get(cls, agent_id: str) -> BaseAgent | None:
        """Look up an agent by id. Returns None if not found."""
        return cls._agents.get(agent_id)

    @classmethod
    def list_agents(cls) -> list[dict]:
        """Return lightweight agent info for the frontend agent list."""
        return [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "description": a.description,
            }
            for a in cls._agents.values()
        ]

    @classmethod
    def default_agent_id(cls) -> str:
        """Return the default agent id. Falls back to 'chat' if no agents registered."""
        if cls._agents:
            return next(iter(cls._agents))
        return CHAT_AGENT_ID
