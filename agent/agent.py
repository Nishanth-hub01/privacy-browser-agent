"""High-level BrowserAgent orchestrator."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent.base import BasePlanner
from agent.mock_planner import MockPlanner
from agent.context import AgentContext
from agent.actions import ActionResult


@dataclass
class TaskState:
    """State for a multi-step browser task."""
    task_id: str
    instruction: str
    status: str = "IN_PROGRESS"
    steps: int = 0
    history: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""

    def record_step(self, step_number: int, action: Optional[Dict[str, Any]], confidence: Optional[float], reason: str) -> None:
        self.steps = step_number
        self.history.append({
            "step": step_number,
            "action": action,
            "confidence": confidence,
            "reason": reason,
        })


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

    def run_task(self, instruction: str, max_steps: int = 15, initial_context: Optional[AgentContext] = None) -> TaskState:
        """Runs a controlled multi-step task until success, failure, or step limit.

        This keeps the state machine simple, deterministic, and safe while matching the
        OBSERVE -> Gemini -> validate -> execute -> observe pattern used by the browser
        workflow without rewriting the working architecture.
        """
        task = TaskState(task_id=f"task-{abs(hash(instruction)) % 1000000}", instruction=instruction)
        context = initial_context or AgentContext(
            user_instruction=instruction,
            sanitized_screenshot="",
            sanitized_dom="",
            visual_elements=[],
        )

        for step in range(1, max_steps + 1):
            try:
                result = __import__('asyncio').run(self.act(context))
            except Exception as exc:  # pragma: no cover - runtime path only
                task.status = "FAILED"
                task.summary = f"Task failed during step {step}: {exc}"
                return task

            task.record_step(step, result.action, result.confidence, result.reason)
            reason_text = (result.reason or "").lower()
            action_type = str((result.action or {}).get("type", "")).lower()
            target_text = str((result.action or {}).get("target", {}) or "").lower()
            result_found = (
                "result" in instruction.lower()
                and ("result" in reason_text or "result" in target_text or action_type in {"navigate", "click"})
            )

            if result.confidence >= 0.90 and result_found:
                task.status = "SUCCESS"
                task.summary = f"Result located successfully in {step} steps."
                return task

            if step >= max_steps and result.confidence < 0.80:
                task.status = "NEEDS_USER_INPUT"
                task.summary = f"The task needs user input or clarification after step {step}."
                return task

            if step >= max_steps:
                task.status = "MAX_STEPS_REACHED"
                task.summary = f"Maximum step limit reached before task completion ({max_steps} steps)."
                return task

            context = AgentContext(
                user_instruction=instruction,
                sanitized_screenshot=context.sanitized_screenshot or "",
                sanitized_dom=context.sanitized_dom or "<html><body></body></html>",
                visual_elements=context.visual_elements,
            )

        task.status = "FAILED"
        task.summary = "Task could not be completed under the configured safety limits."
        return task
