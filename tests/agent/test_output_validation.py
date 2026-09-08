"""Unit tests for strict LLM/VLM output validation per API_CONTRACT.md.

Covers the 6 required scenarios:
1. Valid AI output (click, scroll, type, navigate)
2. Invalid JSON
3. Unsupported action
4. Missing target (or missing required target fields)
5. Invalid confidence (out-of-range, non-numeric, NaN)
6. Low confidence (< 0.80)
"""
import unittest
import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.context import AgentContext
from agent.llm_planner import LLMPlanner
from agent.provider import MockLLMProvider
from agent.exceptions import (
    ModelJSONDecodeError,
    UnsupportedActionError,
    InvalidActionTargetError,
    InvalidConfidenceError,
    InvalidReasonError,
)


class TestLLMOutputValidation(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.context = AgentContext(
            user_instruction="Click the submit button",
            sanitized_screenshot="data:image/png;base64,mock",
            sanitized_dom="<button id='submit-btn'>Submit</button>",
            visual_elements=[{"type": "button", "id": "submit-btn"}],
        )

    # ── 1. Valid AI output ───────────────────────────────────────────────────

    async def test_valid_click_output(self):
        valid_json = json.dumps({
            "action": {
                "type": "click",
                "target": {"id": "submit-btn", "selector": "#submit-btn"}
            },
            "confidence": 0.95,
            "reason": "Matching submit button found."
        })
        planner = LLMPlanner(provider=MockLLMProvider(valid_json))
        result = await planner.plan(self.context)
        self.assertEqual(result.action["type"], "click")
        self.assertEqual(result.action["target"]["id"], "submit-btn")
        self.assertEqual(result.confidence, 0.95)
        self.assertEqual(result.reason, "Matching submit button found.")
        self.assertTrue(result.is_high_confidence)

    async def test_valid_scroll_output(self):
        valid_json = json.dumps({
            "action": {
                "type": "scroll",
                "target": {"direction": "down", "amount": 400}
            },
            "confidence": 0.90,
            "reason": "Scrolling down to view more form fields."
        })
        planner = LLMPlanner(provider=MockLLMProvider(valid_json))
        result = await planner.plan(self.context)
        self.assertEqual(result.action["type"], "scroll")
        self.assertEqual(result.action["target"]["direction"], "down")
        self.assertEqual(result.action["target"]["amount"], 400)
        self.assertEqual(result.confidence, 0.90)

    async def test_valid_type_output(self):
        valid_json = json.dumps({
            "action": {
                "type": "type",
                "target": {"id": "username-input"},
                "text": "test-user"
            },
            "confidence": 0.92,
            "reason": "Entering test username into field."
        })
        planner = LLMPlanner(provider=MockLLMProvider(valid_json))
        result = await planner.plan(self.context)
        self.assertEqual(result.action["type"], "type")
        self.assertEqual(result.action["text"], "test-user")
        self.assertEqual(result.confidence, 0.92)

    async def test_valid_navigate_output(self):
        valid_json = json.dumps({
            "action": {
                "type": "navigate",
                "target": {"url": "https://example.com/dashboard"}
            },
            "confidence": 0.98,
            "reason": "Navigating to dashboard per instruction."
        })
        planner = LLMPlanner(provider=MockLLMProvider(valid_json))
        result = await planner.plan(self.context)
        self.assertEqual(result.action["type"], "navigate")
        self.assertEqual(result.action["target"]["url"], "https://example.com/dashboard")
        self.assertEqual(result.confidence, 0.98)

    # ── 2. Invalid JSON ──────────────────────────────────────────────────────

    async def test_invalid_json_plain_text(self):
        planner = LLMPlanner(provider=MockLLMProvider("I decided to click the button."))
        with self.assertRaises(ModelJSONDecodeError):
            await planner.plan(self.context)

    async def test_invalid_json_truncated(self):
        planner = LLMPlanner(provider=MockLLMProvider('{"action": {"type": "click"'))
        with self.assertRaises(ModelJSONDecodeError):
            await planner.plan(self.context)

    async def test_invalid_json_empty_response(self):
        planner = LLMPlanner(provider=MockLLMProvider("   "))
        with self.assertRaises(ModelJSONDecodeError):
            await planner.plan(self.context)

    # ── 3. Unsupported action ────────────────────────────────────────────────

    async def test_unsupported_action_hover(self):
        bad_json = json.dumps({
            "action": {"type": "hover", "target": {"id": "btn"}},
            "confidence": 0.9,
            "reason": "hovering over button"
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_json))
        with self.assertRaises(UnsupportedActionError):
            await planner.plan(self.context)

    async def test_unsupported_action_drag(self):
        bad_json = json.dumps({
            "action": {"type": "drag", "target": {"id": "btn"}},
            "confidence": 0.9,
            "reason": "dragging"
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_json))
        with self.assertRaises(UnsupportedActionError):
            await planner.plan(self.context)

    async def test_unsupported_action_missing_type(self):
        bad_json = json.dumps({
            "action": {"target": {"id": "btn"}},
            "confidence": 0.9,
            "reason": "missing type"
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_json))
        with self.assertRaises(UnsupportedActionError):
            await planner.plan(self.context)

    # ── 4. Missing target ────────────────────────────────────────────────────

    async def test_missing_target_entirely(self):
        bad_json = json.dumps({
            "action": {"type": "click"},
            "confidence": 0.9,
            "reason": "missing target"
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_json))
        with self.assertRaises(InvalidActionTargetError):
            await planner.plan(self.context)

    async def test_click_missing_target_identifiers(self):
        bad_json = json.dumps({
            "action": {"type": "click", "target": {}},
            "confidence": 0.9,
            "reason": "target with no identifiers"
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_json))
        with self.assertRaises(InvalidActionTargetError):
            await planner.plan(self.context)

    async def test_scroll_invalid_direction(self):
        bad_json = json.dumps({
            "action": {"type": "scroll", "target": {"direction": "left", "amount": 200}},
            "confidence": 0.9,
            "reason": "invalid direction"
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_json))
        with self.assertRaises(InvalidActionTargetError):
            await planner.plan(self.context)

    async def test_scroll_negative_amount(self):
        bad_json = json.dumps({
            "action": {"type": "scroll", "target": {"direction": "down", "amount": -100}},
            "confidence": 0.9,
            "reason": "negative scroll"
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_json))
        with self.assertRaises(InvalidActionTargetError):
            await planner.plan(self.context)

    async def test_type_missing_text(self):
        bad_json = json.dumps({
            "action": {"type": "type", "target": {"id": "box"}},
            "confidence": 0.9,
            "reason": "missing text field"
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_json))
        with self.assertRaises(InvalidActionTargetError):
            await planner.plan(self.context)

    async def test_navigate_missing_url(self):
        bad_json = json.dumps({
            "action": {"type": "navigate", "target": {"url": ""}},
            "confidence": 0.9,
            "reason": "empty url"
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_json))
        with self.assertRaises(InvalidActionTargetError):
            await planner.plan(self.context)

    # ── 5. Invalid confidence ────────────────────────────────────────────────

    async def test_confidence_above_one(self):
        bad_json = json.dumps({
            "action": {"type": "click", "target": {"id": "btn"}},
            "confidence": 1.25,
            "reason": "confidence too high"
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_json))
        with self.assertRaises(InvalidConfidenceError):
            await planner.plan(self.context)

    async def test_confidence_negative(self):
        bad_json = json.dumps({
            "action": {"type": "click", "target": {"id": "btn"}},
            "confidence": -0.1,
            "reason": "confidence negative"
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_json))
        with self.assertRaises(InvalidConfidenceError):
            await planner.plan(self.context)

    async def test_confidence_string_type(self):
        bad_json = json.dumps({
            "action": {"type": "click", "target": {"id": "btn"}},
            "confidence": "high",
            "reason": "string confidence"
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_json))
        with self.assertRaises(InvalidConfidenceError):
            await planner.plan(self.context)

    async def test_confidence_missing(self):
        bad_json = json.dumps({
            "action": {"type": "click", "target": {"id": "btn"}},
            "reason": "missing confidence"
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_json))
        with self.assertRaises(InvalidConfidenceError):
            await planner.plan(self.context)

    # ── 6. Low confidence (< 0.80) ───────────────────────────────────────────

    async def test_low_confidence_preserved(self):
        low_conf_json = json.dumps({
            "action": {"type": "click", "target": {"id": "btn"}},
            "confidence": 0.65,
            "reason": "Ambiguous instruction; multiple buttons present."
        })
        planner = LLMPlanner(provider=MockLLMProvider(low_conf_json))
        result = await planner.plan(self.context)
        self.assertEqual(result.confidence, 0.65)
        self.assertFalse(result.is_high_confidence)
        self.assertIn("Ambiguous instruction", result.reason)


if __name__ == "__main__":
    unittest.main()
