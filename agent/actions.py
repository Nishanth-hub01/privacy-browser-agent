"""Action result models for the agent."""
from dataclasses import dataclass, field
from typing import Any, Dict

# Confidence threshold from API_CONTRACT.md Section 9.
# Actions below this value must NOT be auto-executed; clarification is required.
CONFIDENCE_THRESHOLD: float = 0.80


@dataclass
class ActionResult:
    """Structured decision returned by the agent planner.

    Attributes:
        action: Structured browser action matching API_CONTRACT.md format
                (e.g., click, scroll, type, navigate).
        confidence: Floating point confidence score. Must be in [0.0, 1.0].
        reason: Plain-text explanation of why this action was chosen.
    """
    action: Dict[str, Any]
    confidence: float
    reason: str

    def __post_init__(self) -> None:
        """Validate that confidence is within the legal range [0.0, 1.0]."""
        if not isinstance(self.confidence, (int, float)):
            raise TypeError(
                f"confidence must be a float, got {type(self.confidence).__name__!r}."
            )
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got {self.confidence}."
            )
        self.confidence = float(self.confidence)

    @property
    def is_high_confidence(self) -> bool:
        """Returns True when confidence meets the 0.80 execution threshold."""
        return self.confidence >= CONFIDENCE_THRESHOLD
