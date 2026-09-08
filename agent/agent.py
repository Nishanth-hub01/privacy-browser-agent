"""High-level BrowserAgent orchestrator."""
from typing import Optional
from agent.base import BasePlanner
from agent.mock_planner import MockPlanner
from agent.context import AgentContext
from agent.actions import ActionResult


class BrowserAgent:
    """Core browser agent orchestrator.

    Coordinates between sanitized browser context inputs and a pluggable
    planner (defaults to deterministic MockPlanner).
    """

    def __init__(self, planner: Optional[BasePlanner] = None):
        self.planner: BasePlanner = planner or MockPlanner()

    async def act(self, context: AgentContext) -> ActionResult:
        """Runs the planning pipeline and returns a structured action."""
        return await self.planner.plan(context)
