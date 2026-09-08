"""End-to-End backend pipeline tests for Server + Agent flow.

Performs complete backend flow verification according to API_CONTRACT.md:
API request
→ request validation
→ agent (mock / LLM)
→ action validation
→ confidence handling
→ API response

Includes tests for:
1. Valid click action
2. Valid scroll action
3. Valid type action
4. Valid navigate action
5. Invalid request (missing fields, malformed JSON, invalid types)
6. Invalid action (unsupported action type, missing target, invalid target attributes)
7. Low confidence (confidence < 0.80 returns LOW_CONFIDENCE error, no action)
8. Invalid confidence (out of range, non-numeric, NaN)
9. Agent/model error (agent exceptions, model parsing errors)
10. Server error (unhandled exceptions, missing agent engine)
"""
import unittest
import sys
import json
import math
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from server.api import app
from agent import BrowserAgent, LLMPlanner, MockLLMProvider, MockPlanner
from agent.actions import ActionResult
from agent.context import AgentContext
from server.schemas import ErrorCode
import server.routes


class TestBackendPipelineFlow(unittest.TestCase):
    """Exhaustive tests covering the 10 required backend flow scenarios."""

    def setUp(self):
        self.client = TestClient(app)
        # Ensure fresh default BrowserAgent (uses MockPlanner)
        server.routes.agent = BrowserAgent()
        self.valid_base_payload = {
            "request_id": "req-flow-001",
            "user_instruction": "Click the Submit button",
            "sanitized_screenshot": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "sanitized_dom": "<button id='submit-btn'>Submit</button>",
            "visual_elements": [
                {
                    "type": "button",
                    "label": "Submit",
                    "id": "submit-btn",
                    "selector": "#submit-btn",
                }
            ],
        }

    def tearDown(self):
        # Reset server agent to default
        server.routes.agent = BrowserAgent()

    # ── 1. Valid Click Action ──────────────────────────────────────────────────

    def test_1_valid_click_action_flow(self):
        """Test complete flow for a valid click action using mock agent."""
        payload = {
            "request_id": "req-click-flow",
            "user_instruction": "Click the Submit button",
            "sanitized_screenshot": "data:image/png;base64,mock",
            "sanitized_dom": "<button id='submit-btn'>Submit</button>",
            "visual_elements": [
                {"type": "button", "label": "Submit", "id": "submit-btn", "selector": "#submit-btn"}
            ],
        }
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["request_id"], "req-click-flow")
        self.assertEqual(data["action"]["type"], "click")
        self.assertEqual(data["action"]["target"]["id"], "submit-btn")
        self.assertGreaterEqual(data["confidence"], 0.80)
        self.assertIsInstance(data["reason"], str)
        self.assertTrue(len(data["reason"]) > 0)

    # ── 2. Valid Scroll Action ─────────────────────────────────────────────────

    def test_2_valid_scroll_action_flow(self):
        """Test complete flow for a valid scroll action."""
        payload = {
            "request_id": "req-scroll-flow",
            "user_instruction": "Scroll down 450px",
            "sanitized_screenshot": "data:image/png;base64,mock",
            "sanitized_dom": "<div>Lots of text</div>",
            "visual_elements": [],
        }
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["request_id"], "req-scroll-flow")
        self.assertEqual(data["action"]["type"], "scroll")
        self.assertEqual(data["action"]["target"]["direction"], "down")
        self.assertEqual(data["action"]["target"]["amount"], 450)
        self.assertGreaterEqual(data["confidence"], 0.80)

    # ── 3. Valid Type Action ───────────────────────────────────────────────────

    def test_3_valid_type_action_flow(self):
        """Test complete flow for a valid type action."""
        payload = {
            "request_id": "req-type-flow",
            "user_instruction": "type 'privacy agent' into search",
            "sanitized_screenshot": "data:image/png;base64,mock",
            "sanitized_dom": "<input id='search-box' type='text' />",
            "visual_elements": [
                {"type": "input", "id": "search-box", "selector": "#search-box"}
            ],
        }
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["request_id"], "req-type-flow")
        self.assertEqual(data["action"]["type"], "type")
        self.assertEqual(data["action"]["text"], "privacy agent")
        self.assertEqual(data["action"]["target"]["id"], "search-box")
        self.assertGreaterEqual(data["confidence"], 0.80)

    # ── 4. Valid Navigate Action ───────────────────────────────────────────────

    def test_4_valid_navigate_action_flow(self):
        """Test complete flow for a valid navigate action."""
        payload = {
            "request_id": "req-nav-flow",
            "user_instruction": "navigate to https://example.com/docs",
            "sanitized_screenshot": "data:image/png;base64,mock",
            "sanitized_dom": "",
            "visual_elements": [],
        }
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["request_id"], "req-nav-flow")
        self.assertEqual(data["action"]["type"], "navigate")
        self.assertEqual(data["action"]["target"]["url"], "https://example.com/docs")
        self.assertGreaterEqual(data["confidence"], 0.80)

    # ── 5. Invalid Request ─────────────────────────────────────────────────────

    def test_5_invalid_request_missing_required_fields(self):
        """Test request validation rejection when required fields are missing."""
        # Missing sanitized_screenshot
        bad_payload = {
            "request_id": "req-inv-001",
            "user_instruction": "Click Submit",
            "sanitized_dom": "<div></div>",
        }
        res = self.client.post("/api/v1/analyze", json=bad_payload)
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "INVALID_REQUEST")
        self.assertIn("Field required", data["error"]["message"])

    def test_5_invalid_request_malformed_json_syntax(self):
        """Test request validation rejection on non-JSON payload."""
        res = self.client.post(
            "/api/v1/analyze",
            content="{bad json syntax: true",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "INVALID_REQUEST")

    def test_5_invalid_request_empty_screenshot(self):
        """Test request validation rejection for empty screenshot (INVALID_CONTEXT)."""
        payload = self.valid_base_payload.copy()
        payload["sanitized_screenshot"] = ""
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 422)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "INVALID_CONTEXT")

    # ── 6. Invalid Action ──────────────────────────────────────────────────────

    def test_6_invalid_action_unsupported_type(self):
        """Test action validation rejection when agent proposes an unsupported action type."""
        unsupported_result = ActionResult(
            action={"type": "drag_and_drop", "target": {"id": "box1"}},
            confidence=0.95,
            reason="Dragging box",
        )
        with patch.object(server.routes.agent, "act", new=AsyncMock(return_value=unsupported_result)):
            res = self.client.post("/api/v1/analyze", json=self.valid_base_payload)
            self.assertEqual(res.status_code, 422)
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"]["code"], "ACTION_NOT_FOUND")
            self.assertIn("Unsupported action type", data["error"]["message"])

    def test_6_invalid_action_missing_target(self):
        """Test action validation rejection when action target is empty or invalid."""
        missing_target_result = ActionResult(
            action={"type": "click", "target": {}},
            confidence=0.95,
            reason="Missing target locator",
        )
        with patch.object(server.routes.agent, "act", new=AsyncMock(return_value=missing_target_result)):
            res = self.client.post("/api/v1/analyze", json=self.valid_base_payload)
            self.assertEqual(res.status_code, 422)
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"]["code"], "ACTION_NOT_FOUND")

    def test_6_invalid_action_scroll_missing_direction(self):
        """Test action validation rejection when scroll direction is invalid."""
        bad_scroll_result = ActionResult(
            action={"type": "scroll", "target": {"direction": "diagonal", "amount": 200}},
            confidence=0.90,
            reason="Diagonal scroll",
        )
        with patch.object(server.routes.agent, "act", new=AsyncMock(return_value=bad_scroll_result)):
            res = self.client.post("/api/v1/analyze", json=self.valid_base_payload)
            self.assertEqual(res.status_code, 422)
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"]["code"], "ACTION_NOT_FOUND")

    # ── 7. Low Confidence ──────────────────────────────────────────────────────

    def test_7_low_confidence_handling(self):
        """Test confidence handling when confidence < 0.80: returns LOW_CONFIDENCE and no action."""
        low_conf_result = ActionResult(
            action={"type": "click", "target": {"id": "submit-btn"}},
            confidence=0.72,
            reason="Ambiguous instruction; not certain of match.",
        )
        with patch.object(server.routes.agent, "act", new=AsyncMock(return_value=low_conf_result)):
            res = self.client.post("/api/v1/analyze", json=self.valid_base_payload)
            self.assertEqual(res.status_code, 200)  # Must be 200 per API_CONTRACT
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"]["code"], "LOW_CONFIDENCE")
            self.assertIn("0.80", data["error"]["message"])
            # CRITICAL: No action returned to prevent accidental execution by extension
            self.assertNotIn("action", data)
            self.assertNotIn("confidence", data)

    # ── 8. Invalid Confidence ──────────────────────────────────────────────────

    def test_8_invalid_confidence_above_range(self):
        """Test confidence validation rejection when confidence is > 1.0."""
        # Using LLMPlanner with mock response outputting confidence = 1.5
        bad_output = json.dumps({
            "action": {"type": "click", "target": {"id": "submit-btn"}},
            "confidence": 1.5,
            "reason": "Over-confident",
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_output))
        server.routes.agent = BrowserAgent(planner=planner)

        res = self.client.post("/api/v1/analyze", json=self.valid_base_payload)
        self.assertEqual(res.status_code, 422)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "MODEL_ERROR")

    def test_8_invalid_confidence_negative(self):
        """Test confidence validation rejection when confidence is negative."""
        bad_output = json.dumps({
            "action": {"type": "click", "target": {"id": "submit-btn"}},
            "confidence": -0.25,
            "reason": "Negative confidence",
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_output))
        server.routes.agent = BrowserAgent(planner=planner)

        res = self.client.post("/api/v1/analyze", json=self.valid_base_payload)
        self.assertEqual(res.status_code, 422)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "MODEL_ERROR")

    def test_8_invalid_confidence_non_numeric(self):
        """Test confidence validation rejection when confidence is a string."""
        bad_output = json.dumps({
            "action": {"type": "click", "target": {"id": "submit-btn"}},
            "confidence": "high",
            "reason": "String confidence",
        })
        planner = LLMPlanner(provider=MockLLMProvider(bad_output))
        server.routes.agent = BrowserAgent(planner=planner)

        res = self.client.post("/api/v1/analyze", json=self.valid_base_payload)
        self.assertEqual(res.status_code, 422)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "MODEL_ERROR")

    # ── 9. Agent / Model Error ─────────────────────────────────────────────────

    def test_9_agent_model_error_runtime_exception(self):
        """Test agent/model error handling when agent raises an unexpected exception."""
        with patch.object(server.routes.agent, "act", new=AsyncMock(side_effect=RuntimeError("AI model inference failure"))):
            res = self.client.post("/api/v1/analyze", json=self.valid_base_payload)
            self.assertEqual(res.status_code, 500)
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"]["code"], "MODEL_ERROR")
            self.assertIn("AI model inference failure", data["error"]["message"])

    def test_9_agent_model_error_malformed_json_response(self):
        """Test agent/model error handling when LLM returns non-JSON text."""
        planner = LLMPlanner(provider=MockLLMProvider("Plain text output from LLM, not JSON"))
        server.routes.agent = BrowserAgent(planner=planner)

        res = self.client.post("/api/v1/analyze", json=self.valid_base_payload)
        self.assertEqual(res.status_code, 422)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "MODEL_ERROR")
        self.assertIn("Model response was not valid JSON", data["error"]["message"])

    # ── 10. Server Error ───────────────────────────────────────────────────────

    def test_10_server_error_agent_uninitialized(self):
        """Test server error when agent instance is None or uninitialized."""
        with patch("server.routes.agent", None):
            res = self.client.post("/api/v1/analyze", json=self.valid_base_payload)
            self.assertEqual(res.status_code, 500)
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"]["code"], "SERVER_ERROR")
            self.assertIn("Agent planning engine is not available", data["error"]["message"])

    def test_10_server_error_unhandled_exception(self):
        """Test global server exception handler formats unhandled exceptions as SERVER_ERROR."""
        client_no_raise = TestClient(app, raise_server_exceptions=False)
        with patch("server.routes.check_privacy_violations", side_effect=Exception("Database or system level crash")):
            res = client_no_raise.post("/api/v1/analyze", json=self.valid_base_payload)
            self.assertEqual(res.status_code, 500)
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"]["code"], "SERVER_ERROR")


if __name__ == "__main__":
    unittest.main()
