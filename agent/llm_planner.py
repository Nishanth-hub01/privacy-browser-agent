import json
import logging
import math
import re
from typing import Any, Dict, Optional

from agent.base import BasePlanner
from agent.context import AgentContext
from agent.actions import ActionResult
from agent.config import AgentConfig
from agent.exceptions import (
    ModelJSONDecodeError,
    UnsupportedActionError,
    InvalidActionTargetError,
    InvalidConfidenceError,
    InvalidReasonError,
)
from agent.prompts import build_multimodal_messages
from agent.provider import BaseLLMProvider, OpenAIProvider, ProviderError
from agent.mock_planner import MockPlanner

logger = logging.getLogger("agent.llm_planner")

SUPPORTED_ACTIONS = ("click", "scroll", "type", "navigate")


class LLMPlanner(BasePlanner):
    """VLM/LLM browser action planner with strict output validation.

    Inspects sanitized screenshot, DOM, and visual elements alongside the
    user's natural language instruction, calls the vision model, and strictly
    validates the structured decision into an ActionResult matching API_CONTRACT.md.
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        provider: Optional[BaseLLMProvider] = None,
    ):
        self.config = config or AgentConfig.from_env()
        self.provider = provider or OpenAIProvider(self.config)
        # Only fall back to MockPlanner if fallback is enabled, no custom provider was injected,
        # and no API key is available.
        self._mock_fallback = (
            MockPlanner()
            if (self.config.fallback_to_mock and provider is None and not self.config.has_api_key)
            else None
        )

    async def plan(self, context: AgentContext) -> ActionResult:
        """Executes the VLM/LLM planning pipeline.

        1. If fallback_to_mock is enabled and no API key is set, use MockPlanner.
        2. Otherwise, construct multimodal messages containing only sanitized data.
        3. Call the configured model provider.
        4. Parse and strictly validate the JSON response.
        5. Return structured ActionResult.
        """
        if self._mock_fallback is not None:
            logger.warning(
                "No API key configured for LLM/VLM provider (%s). "
                "Falling back to deterministic MockPlanner.",
                self.config.provider,
            )
            return await self._mock_fallback.plan(context)

        # Build multimodal prompt with strictly sanitized context
        messages = build_multimodal_messages(context)

        try:
            raw_response = await self.provider.call(messages)
        except Exception as exc:
            if self.config.fallback_to_mock and self._mock_fallback:
                logger.warning(
                    "LLM provider call failed (%s); falling back to MockPlanner.", exc
                )
                return await self._mock_fallback.plan(context)
            raise ProviderError(f"Model planning failed: {exc}") from exc

        return self.parse_model_response(raw_response)

    def parse_model_response(self, raw_response: str) -> ActionResult:
        """Parses and strictly validates the raw JSON response from the model into an ActionResult.

        Validates:
        - action type (strictly: click, scroll, type, navigate)
        - target and required fields for each action type
        - confidence (numeric, between 0.0 and 1.0)
        - reason (non-empty string)

        Args:
            raw_response: Raw string returned by the model.

        Returns:
            Validated ActionResult.

        Raises:
            ModelJSONDecodeError: If JSON is malformed or empty.
            UnsupportedActionError: If action type is unsupported.
            InvalidActionTargetError: If target or required fields are missing.
            InvalidConfidenceError: If confidence is invalid or out of range.
            InvalidReasonError: If reason is missing or empty.
        """
        if not raw_response or not raw_response.strip():
            raise ModelJSONDecodeError("Model returned an empty response.")

        clean_text = raw_response.strip()

        # Strip markdown code blocks if the model wrapped the JSON (e.g., ```json ... ```)
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
            clean_text = re.sub(r"\s*```$", "", clean_text)
            clean_text = clean_text.strip()

        try:
            data = json.loads(clean_text)
        except json.JSONDecodeError as err:
            logger.error("Failed to parse JSON from model response: %s\nRaw: %r", err, raw_response)
            raise ModelJSONDecodeError(f"Model response was not valid JSON: {err}") from err

        if not isinstance(data, dict):
            raise ModelJSONDecodeError(f"Model response JSON must be an object, got {type(data).__name__}")

        # ── 1. Validate 'action' container ──────────────────────────────────
        action_data = data.get("action")
        if not action_data or not isinstance(action_data, dict):
            raise InvalidActionTargetError("Model response is missing required 'action' dictionary.")

        # ── 2. Validate action type ─────────────────────────────────────────
        action_type = action_data.get("type")
        if not action_type or not isinstance(action_type, str):
            raise UnsupportedActionError("Action is missing required 'type' string field.")

        action_type = action_type.strip().lower()
        action_data["type"] = action_type

        if action_type not in SUPPORTED_ACTIONS:
            raise UnsupportedActionError(
                f"Unsupported action type '{action_type}'. "
                f"Only allowed: {', '.join(SUPPORTED_ACTIONS)}."
            )

        # ── 3. Validate target and required fields per action type ─────────
        self._validate_action_target(action_type, action_data)

        # ── 4. Validate confidence score ───────────────────────────────────
        confidence_raw = data.get("confidence")
        if confidence_raw is None:
            raise InvalidConfidenceError("Model response is missing required 'confidence' score.")
        if not isinstance(confidence_raw, (int, float)) or isinstance(confidence_raw, bool):
            raise InvalidConfidenceError(
                f"Confidence score must be numeric, got {type(confidence_raw).__name__!r}."
            )

        confidence = float(confidence_raw)
        if math.isnan(confidence) or math.isinf(confidence) or not (0.0 <= confidence <= 1.0):
            raise InvalidConfidenceError(
                f"Confidence score must be between 0.0 and 1.0, got {confidence}."
            )

        # ── 5. Validate explanation reason ─────────────────────────────────
        reason_raw = data.get("reason")
        if reason_raw is None:
            raise InvalidReasonError("Model response is missing required 'reason' field.")
        if not isinstance(reason_raw, str) or not reason_raw.strip():
            raise InvalidReasonError(
                "Model 'reason' must be a non-empty string explaining the chosen action."
            )
        reason = reason_raw.strip()

        return ActionResult(
            action=action_data,
            confidence=confidence,
            reason=reason,
        )

    def _validate_action_target(self, action_type: str, action: Dict[str, Any]) -> None:
        """Validates that target and all required fields are present and valid."""
        target = action.get("target")
        if target is None or not isinstance(target, dict):
            raise InvalidActionTargetError(
                f"Action '{action_type}' requires a non-null 'target' dictionary."
            )

        if action_type == "click":
            # Must specify at least one target identifier
            has_id = bool(target.get("id"))
            has_selector = bool(target.get("selector"))
            has_coords = target.get("x") is not None and target.get("y") is not None
            if not (has_id or has_selector or has_coords):
                raise InvalidActionTargetError(
                    "Click target must specify at least one identifier: 'id', 'selector', or ('x' and 'y')."
                )

        elif action_type == "scroll":
            direction = target.get("direction")
            if not direction or str(direction).lower() not in ("up", "down"):
                raise InvalidActionTargetError(
                    f"Scroll action target requires direction 'up' or 'down', got {direction!r}."
                )
            target["direction"] = str(direction).lower()

            amount = target.get("amount")
            if amount is None or isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
                raise InvalidActionTargetError(
                    f"Scroll action target requires a positive numeric 'amount', got {amount!r}."
                )
            target["amount"] = int(amount)

        elif action_type == "type":
            # Target must have an element identifier
            has_id = bool(target.get("id"))
            has_selector = bool(target.get("selector"))
            has_coords = target.get("x") is not None and target.get("y") is not None
            if not (has_id or has_selector or has_coords):
                raise InvalidActionTargetError(
                    "Type target must specify at least one identifier: 'id', 'selector', or ('x' and 'y')."
                )

            text = action.get("text")
            if text is None or not isinstance(text, str):
                raise InvalidActionTargetError(
                    "Type action requires a 'text' string field."
                )

        elif action_type == "navigate":
            url = target.get("url")
            if not url or not isinstance(url, str) or not url.strip():
                raise InvalidActionTargetError(
                    "Navigate action requires a non-empty 'url' string in target."
                )
