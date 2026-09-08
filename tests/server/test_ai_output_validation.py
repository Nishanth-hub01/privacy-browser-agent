"""API integration tests for strict AI output validation via POST /api/v1/analyze.

Verifies server pipeline response for the 6 required scenarios:
1. Valid AI output
2. Invalid JSON
3. Unsupported action
4. Missing target
5. Invalid confidence
6. Low confidence
"""
import unittest
import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from server.api import app
from agent import BrowserAgent, LLMPlanner, MockLLMProvider
import server.routes


class TestAPIOutputValidation(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.payload = {
            "request_id": "req-val-001",
            "user_instruction": "Click the Submit button",
            "sanitized_screenshot": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "sanitized_dom": "<button id='submit-btn'>Submit</button>",
            "visual_elements": [
                {"type": "button", "label": "Submit", "id": "submit-btn"}
            ],
        }

    def _set_agent_response(self, response_text: str):
        planner = LLMPlanner(provider=MockLLMProvider(response_text))
        server.routes.agent = BrowserAgent(planner=planner)

    def tearDown(self):
        # Reset agent to default
        server.routes.agent = BrowserAgent()

    # ── 1. Valid AI output ───────────────────────────────────────────────────

    def test_valid_ai_output(self):
        self._set_agent_response(json.dumps({
            "action": {"type": "click", "target": {"id": "submit-btn"}},
            "confidence": 0.95,
            "reason": "Matching submit button found"
        }))
        res = self.client.post("/api/v1/analyze", json=self.payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"]["type"], "click")
        self.assertEqual(data["action"]["target"]["id"], "submit-btn")
        self.assertEqual(data["confidence"], 0.95)

    # ── 2. Invalid JSON ──────────────────────────────────────────────────────

    def test_invalid_json_model_output(self):
        self._set_agent_response("This is not JSON at all.")
        res = self.client.post("/api/v1/analyze", json=self.payload)
        self.assertEqual(res.status_code, 422)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "MODEL_ERROR")

    # ── 3. Unsupported action ────────────────────────────────────────────────

    def test_unsupported_action(self):
        self._set_agent_response(json.dumps({
            "action": {"type": "hover_and_wait", "target": {"id": "submit-btn"}},
            "confidence": 0.95,
            "reason": "Hover action"
        }))
        res = self.client.post("/api/v1/analyze", json=self.payload)
        self.assertEqual(res.status_code, 422)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "ACTION_NOT_FOUND")

    # ── 4. Missing target ────────────────────────────────────────────────────

    def test_missing_target(self):
        self._set_agent_response(json.dumps({
            "action": {"type": "click", "target": {}},
            "confidence": 0.95,
            "reason": "Missing target identifiers"
        }))
        res = self.client.post("/api/v1/analyze", json=self.payload)
        self.assertEqual(res.status_code, 422)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "ACTION_NOT_FOUND")

    # ── 5. Invalid confidence ────────────────────────────────────────────────

    def test_invalid_confidence_above_one(self):
        self._set_agent_response(json.dumps({
            "action": {"type": "click", "target": {"id": "submit-btn"}},
            "confidence": 2.5,
            "reason": "Out of range confidence"
        }))
        res = self.client.post("/api/v1/analyze", json=self.payload)
        self.assertEqual(res.status_code, 422)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "MODEL_ERROR")

    def test_invalid_confidence_string(self):
        self._set_agent_response(json.dumps({
            "action": {"type": "click", "target": {"id": "submit-btn"}},
            "confidence": "very_confident",
            "reason": "Non-numeric confidence"
        }))
        res = self.client.post("/api/v1/analyze", json=self.payload)
        self.assertEqual(res.status_code, 422)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "MODEL_ERROR")

    # ── 6. Low confidence ────────────────────────────────────────────────────

    def test_low_confidence(self):
        self._set_agent_response(json.dumps({
            "action": {"type": "click", "target": {"id": "submit-btn"}},
            "confidence": 0.65,
            "reason": "Target ambiguous"
        }))
        res = self.client.post("/api/v1/analyze", json=self.payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "LOW_CONFIDENCE")
        # Ensure no action is returned when confidence is below 0.80
        self.assertNotIn("action", data)
        self.assertIn("0.80", data["error"]["message"])


if __name__ == "__main__":
    unittest.main()
