"""Abstract base class for agent planners."""
from abc import ABC, abstractmethod
from agent.context import AgentContext
from agent.actions import ActionResult


class BasePlanner(ABC):
    """Abstract planner interface.

    Both deterministic/mock planners and future VLM/LLM-based planners
    implement this interface to generate structured browser actions.
    """

    @abstractmethod
    async def plan(self, context: AgentContext) -> ActionResult:
        """Analyze the sanitized context and decide the next browser action.

        Args:
            context: Sanitized multimodal context from the browser.

        Returns:
            ActionResult containing the structured action, confidence, and reason.
        """
        pass
