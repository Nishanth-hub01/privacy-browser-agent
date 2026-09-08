"""Exhaustive test suite for Server Error Handling and API_CONTRACT.md compliance.

Covers all 5 core cases and 7 error codes:
1. INVALID_REQUEST       - Malformed JSON, missing required fields, invalid types
2. INVALID_CONTEXT       - Empty screenshot, missing DOM, empty instruction
3. PRIVACY_CHECK_FAILED  - Raw passwords or PII detected in incoming payload
4. MODEL_ERROR           - Agent raises exception, invalid/out-of-range confidence
5. ACTION_NOT_FOUND      - Empty action, unsupported action type, invalid action schema
6. LOW_CONFIDENCE        - Confidence < 0.80 returns LOW_CONFIDENCE and no action field
7. SERVER_ERROR          - Agent engine missing/misconfigured, unexpected server errors
"""
import unittest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from server.api import app
from agent.actions import ActionResult


class TestErrorHandling(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.valid_payload = {
            "request_id": "req-err-001",
            "user_instruction": "Click the Submit button",
            "sanitized_screenshot": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "sanitized_dom": "<button id='submit-btn'>Submit</button>",
            "visual_elements": [
                {"type": "button", "label": "Submit", "id": "submit-btn"}
            ],
        }

    # ─── CASE 1: INVALID_REQUEST ───────────────────────────────────────────────

    def test_missing_request_id(self):
        payload = self.valid_payload.copy()
        del payload["request_id"]
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "INVALID_REQUEST")

    def test_missing_user_instruction(self):
        payload = self.valid_payload.copy()
        del payload["user_instruction"]
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "INVALID_REQUEST")

    def test_missing_sanitized_screenshot(self):
        payload = self.valid_payload.copy()
        del payload["sanitized_screenshot"]
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "INVALID_REQUEST")

    def test_malformed_json_body(self):
        res = self.client.post(
            "/api/v1/analyze",
            content="NOT_VALID_JSON_AT_ALL",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "INVALID_REQUEST")

    # ─── CASE 2: INVALID_CONTEXT & PRIVACY_CHECK_FAILED ────────────────────────

    def test_empty_screenshot(self):
        payload = self.valid_payload.copy()
        payload["sanitized_screenshot"] = ""
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 422)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "INVALID_CONTEXT")

    def test_whitespace_only_instruction(self):
        payload = self.valid_payload.copy()
        payload["user_instruction"] = "    "
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 422)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "INVALID_CONTEXT")

    def test_privacy_check_failed_password_in_dom(self):
        payload = self.valid_payload.copy()
        payload["sanitized_dom"] = "<input type='password' value='MySecretPass123'> Password: MySecretPass123"
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "PRIVACY_CHECK_FAILED")

    def test_privacy_check_failed_password_in_instruction(self):
        payload = self.valid_payload.copy()
        payload["user_instruction"] = "Enter password: SecretAdmin999"
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "PRIVACY_CHECK_FAILED")

    # ─── CASE 3: ACTION_NOT_FOUND (UNSUPPORTED / INVALID ACTIONS) ───────────────

    def test_action_not_found_unsupported_action_type(self):
        mock_result = ActionResult(
            action={"type": "drag_and_drop", "target": {"id": "box"}},
            confidence=0.90,
            reason="Unsupported action",
        )
        with patch("server.routes.agent") as mock_agent:
            mock_agent.act = AsyncMock(return_value=mock_result)
            res = self.client.post("/api/v1/analyze", json=self.valid_payload)
            self.assertEqual(res.status_code, 422)
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"]["code"], "ACTION_NOT_FOUND")

    def test_action_not_found_empty_action(self):
        mock_result = ActionResult(
            action={},
            confidence=0.90,
            reason="Empty action",
        )
        with patch("server.routes.agent") as mock_agent:
            mock_agent.act = AsyncMock(return_value=mock_result)
            res = self.client.post("/api/v1/analyze", json=self.valid_payload)
            self.assertEqual(res.status_code, 422)
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"]["code"], "ACTION_NOT_FOUND")

    def test_action_not_found_invalid_scroll_direction(self):
        mock_result = ActionResult(
            action={"type": "scroll", "target": {"direction": "sideways", "amount": 200}},
            confidence=0.90,
            reason="Bad scroll direction",
        )
        with patch("server.routes.agent") as mock_agent:
            mock_agent.act = AsyncMock(return_value=mock_result)
            res = self.client.post("/api/v1/analyze", json=self.valid_payload)
            self.assertEqual(res.status_code, 422)
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"]["code"], "ACTION_NOT_FOUND")

    def test_action_not_found_missing_click_target(self):
        mock_result = ActionResult(
            action={"type": "click"},
            confidence=0.90,
            reason="Missing target",
        )
        with patch("server.routes.agent") as mock_agent:
            mock_agent.act = AsyncMock(return_value=mock_result)
            res = self.client.post("/api/v1/analyze", json=self.valid_payload)
            self.assertEqual(res.status_code, 422)
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"]["code"], "ACTION_NOT_FOUND")

    # ─── CASE 4: MODEL_ERROR ───────────────────────────────────────────────────

    def test_model_error_agent_exception(self):
        with patch("server.routes.agent") as mock_agent:
            mock_agent.act = AsyncMock(side_effect=RuntimeError("Neural model inference crashed"))
            res = self.client.post("/api/v1/analyze", json=self.valid_payload)
            self.assertEqual(res.status_code, 500)
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"]["code"], "MODEL_ERROR")
            self.assertIn("Neural model inference crashed", data["error"]["message"])

    def test_model_error_invalid_confidence_type(self):
        # Fake an ActionResult with corrupted non-numeric confidence
        fake_res = ActionResult(
            action={"type": "click", "target": {"id": "btn"}},
            confidence=0.9,
            reason="test",
        )
        fake_res.confidence = "not-a-number"  # bypass init validation
        with patch("server.routes.agent") as mock_agent:
            mock_agent.act = AsyncMock(return_value=fake_res)
            res = self.client.post("/api/v1/analyze", json=self.valid_payload)
            self.assertEqual(res.status_code, 422)
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"]["code"], "MODEL_ERROR")

    # ─── CASE 5: LOW_CONFIDENCE ────────────────────────────────────────────────

    def test_low_confidence_below_080(self):
        mock_result = ActionResult(
            action={"type": "click", "target": {"id": "btn"}},
            confidence=0.72,
            reason="Uncertain match",
        )
        with patch("server.routes.agent") as mock_agent:
            mock_agent.act = AsyncMock(return_value=mock_result)
            res = self.client.post("/api/v1/analyze", json=self.valid_payload)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"]["code"], "LOW_CONFIDENCE")
            # Must NEVER return action object when low confidence
            self.assertNotIn("action", data)
            self.assertIn("0.80", data["error"]["message"])

    # ─── CASE 6: SERVER_ERROR ──────────────────────────────────────────────────

    def test_server_error_agent_unavailable(self):
        with patch("server.routes.agent", None):
            res = self.client.post("/api/v1/analyze", json=self.valid_payload)
            self.assertEqual(res.status_code, 500)
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"]["code"], "SERVER_ERROR")

    def test_server_error_catchall_handler(self):
        """Verify global exception handler formats unexpected errors into SERVER_ERROR."""
        client = TestClient(app, raise_server_exceptions=False)
        with patch("server.routes.check_privacy_violations", side_effect=Exception("Critical system failure")):
            res = client.post("/api/v1/analyze", json=self.valid_payload)
            self.assertEqual(res.status_code, 500)
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"]["code"], "SERVER_ERROR")


if __name__ == "__main__":
    unittest.main()
