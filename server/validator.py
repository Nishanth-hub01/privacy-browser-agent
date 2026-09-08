"""Validation utilities for privacy boundaries, context integrity, action schemas, and confidence.

Privacy integration notes (API_CONTRACT.md §3 and §6):
  - The server accepts ONLY sanitized fields: sanitized_screenshot, sanitized_dom,
    visual_elements, and user_instruction.
  - Raw screenshots, raw DOM, or any raw PII must never reach this module.
  - check_privacy_violations() is the server's last-resort safety gate.
    The Privacy module (privacy/) is the primary sanitization layer.
  - When the Privacy module is ready, server/privacy_interface.py defines
    the SanitizedContext interface and verify_sanitized_context() entry point.
"""
from typing import Any, Optional

try:
    from server.schemas import (
        AnalyzeRequest,
        BrowserAction,
        ClickAction,
        ScrollAction,
        TypeAction,
        NavigateAction,
    )
    from server.privacy_interface import check_sanitized_fields
except ModuleNotFoundError:
    from schemas import (
        AnalyzeRequest,
        BrowserAction,
        ClickAction,
        ScrollAction,
        TypeAction,
        NavigateAction,
    )
    from privacy_interface import check_sanitized_fields

# Matches API_CONTRACT.md Section 9: confidence must be in [0.0, 1.0]
CONFIDENCE_MIN: float = 0.0
CONFIDENCE_MAX: float = 1.0
CONFIDENCE_THRESHOLD: float = 0.80

# Minimum acceptable byte-lengths for sanitized content
_MIN_SCREENSHOT_LEN: int = 10
_MIN_DOM_LEN: int = 0


def check_privacy_violations(request: AnalyzeRequest) -> Optional[str]:
    """Server-side last-resort PII guard (per API_CONTRACT.md §3).

    Delegates to server.privacy_interface.check_sanitized_fields which scans
    sanitized_dom and user_instruction for common unredacted patterns:
      - Passwords   (e.g. "password: MySecret123")
      - Email addresses (e.g. "user@example.com")
      - Phone numbers (e.g. "+1 800 555 0100")
      - Credit/debit card numbers (e.g. "4111 1111 1111 1111")

    The Privacy module (privacy/) is the primary sanitization layer and must
    have already replaced these with safe tokens like [REDACTED], [EMAIL],
    [PHONE], [CARD] before the Extension sends the request.

    Returns:
        str describing the violation if raw sensitive data is detected, else None.
    """
    return check_sanitized_fields(
        sanitized_screenshot=request.sanitized_screenshot,
        sanitized_dom=request.sanitized_dom,
        user_instruction=request.user_instruction,
    )


def check_context_validity(request: AnalyzeRequest) -> Optional[str]:
    """Validates that the sanitized context is processable by the AI agent.

    Per API_CONTRACT.md error code INVALID_CONTEXT: returned when the
    sanitized context cannot be processed.

    Returns an error message string if context is invalid, or None if valid.
    """
    if not request.sanitized_screenshot or len(request.sanitized_screenshot.strip()) < _MIN_SCREENSHOT_LEN:
        return (
            "sanitized_screenshot is empty or too short to be a valid image. "
            "Ensure the privacy module sends a base64-encoded redacted screenshot."
        )

    if request.sanitized_dom is None:
        return (
            "sanitized_dom is missing. "
            "Ensure the privacy module sends sanitized HTML content."
        )

    if not request.user_instruction or not request.user_instruction.strip():
        return "user_instruction is empty. A non-empty instruction is required for action planning."

    return None


def validate_confidence(confidence: Any) -> float:
    """Validates and returns a clean confidence float per API_CONTRACT.md Section 9.

    Confidence must be a numeric value in [0.0, 1.0].
    Raises:
        TypeError: if the value is not numeric.
        ValueError: if the value is outside [0.0, 1.0].
    """
    if not isinstance(confidence, (int, float)):
        raise TypeError(
            f"confidence must be a numeric value, got {type(confidence).__name__!r}."
        )
    confidence = float(confidence)
    if not (CONFIDENCE_MIN <= confidence <= CONFIDENCE_MAX):
        raise ValueError(
            f"confidence must be between {CONFIDENCE_MIN} and {CONFIDENCE_MAX}, got {confidence}."
        )
    return confidence


def is_low_confidence(confidence: float) -> bool:
    """Returns True when confidence falls below the 0.80 auto-execution threshold.

    Per API_CONTRACT.md Section 9: confidence < 0.80 → ask user / request clarification.
    """
    return confidence < CONFIDENCE_THRESHOLD


def validate_browser_action(action_data: Any) -> BrowserAction:
    """Validates that action_data strictly matches supported BrowserAction models.

    Supported types: click, scroll, type, navigate.
    Raises ValueError or Pydantic ValidationError if invalid.
    """
    if not isinstance(action_data, dict):
        raise ValueError("Action must be a dictionary object.")

    action_type = action_data.get("type")
    if not action_type or not isinstance(action_type, str):
        raise ValueError("Action is missing required 'type' field.")

    action_type = action_type.strip().lower()
    if action_type not in ("click", "scroll", "type", "navigate"):
        raise ValueError(
            f"Unsupported action type '{action_type}'. Supported actions: click, scroll, type, navigate."
        )

    if action_type == "click":
        validated = ClickAction.model_validate(action_data)
        t = validated.target
        if not (t.id or t.selector or (t.x is not None and t.y is not None)):
            raise ValueError("Click target must specify at least one identifier: id, selector, or (x, y).")
        return validated

    elif action_type == "scroll":
        validated = ScrollAction.model_validate(action_data)
        if validated.target.amount <= 0:
            raise ValueError("Scroll amount must be a positive integer.")
        return validated

    elif action_type == "type":
        validated = TypeAction.model_validate(action_data)
        if not validated.text or not isinstance(validated.text, str):
            raise ValueError("Type action requires a non-empty 'text' string.")
        t = validated.target
        if not (t.id or t.selector or (t.x is not None and t.y is not None)):
            raise ValueError("Type target must specify at least one identifier: id, selector, or (x, y).")
        return validated

    elif action_type == "navigate":
        validated = NavigateAction.model_validate(action_data)
        if not validated.target.url or not validated.target.url.strip():
            raise ValueError("Navigate action requires a non-empty 'url' string.")
        return validated

    else:
        raise ValueError(f"Unknown action type: {action_type}")

