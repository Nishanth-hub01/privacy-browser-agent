"""Agent context data model holding sanitized inputs."""
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentContext:
    """Encapsulates all sanitized browser context passed into the agent.

    Attributes:
        user_instruction: The user's natural language objective.
        sanitized_screenshot: Base64-encoded screenshot with sensitive areas redacted.
        sanitized_dom: Sanitized HTML DOM string.
        visual_elements: List of detected UI element descriptors.
    """
    user_instruction: str
    sanitized_screenshot: str
    sanitized_dom: str
    visual_elements: List[Dict[str, Any]] = field(default_factory=list)
