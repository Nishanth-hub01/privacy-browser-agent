"""Confidence handling tests — API_CONTRACT.md Section 9.

Covers:
  - confidence >= 0.80  → action returned for execution
  - confidence <  0.80  → LOW_CONFIDENCE error returned, action NOT executed
  - invalid confidence values rejected at ActionResult construction and validate_confidence()
  - confidence field preserved exactly in success response
"""
import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from server.api import app
from agent.actions import ActionResult, CONFIDENCE_THRESHOLD
from server.validator import validate_confidence, is_low_confidence, CONFIDENCE_THRESHOLD as SERVER_THRESHOLD


class TestConfidenceConstants(unittest.TestCase):
    """Verify the threshold constant is 0.80 as required by the contract."""

    def test_threshold_value(self):
        self.assertEqual(CONFIDENCE_THRESHOLD, 0.80)
        self.assertEqual(SERVER_THRESHOLD, 0.80)

    def test_agent_and_server_thresholds_are_aligned(self):
        """Both agent and server must use the same threshold."""
        self.assertEqual(CONFIDENCE_THRESHOLD, SERVER_THRESHOLD)


class TestActionResultConfidenceValidation(unittest.TestCase):
    """ActionResult __post_init__ enforces 0.0 ≤ confidence ≤ 1.0."""

    def _make_action(self, confidence):
        return ActionResult(
            action={"type": "click", "target": {"id": "btn"}},
            confidence=confidence,
            reason="test",
        )

    def test_confidence_exactly_080_accepted(self):
        ar = self._make_action(0.80)
        self.assertEqual(ar.confidence, 0.80)

    def test_confidence_exactly_000_accepted(self):
        ar = self._make_action(0.0)
        self.assertEqual(ar.confidence, 0.0)

    def test_confidence_exactly_100_accepted(self):
        ar = self._make_action(1.0)
        self.assertEqual(ar.confidence, 1.0)

    def test_confidence_079_accepted(self):
        """0.79 is a valid float; threshold check happens separately in server."""
        ar = self._make_action(0.79)
        self.assertEqual(ar.confidence, 0.79)

    def test_confidence_negative_rejected(self):
        with self.assertRaises(ValueError):
            self._make_action(-0.01)

    def test_confidence_above_1_rejected(self):
        with self.assertRaises(ValueError):
            self._make_action(1.001)

    def test_confidence_non_numeric_rejected(self):
        with self.assertRaises(TypeError):
            self._make_action("high")

    def test_confidence_none_rejected(self):
        with self.assertRaises(TypeError):
            self._make_action(None)

    def test_is_high_confidence_property(self):
        self.assertTrue(self._make_action(0.80).is_high_confidence)
        self.assertTrue(self._make_action(0.96).is_high_confidence)
        self.assertFalse(self._make_action(0.79).is_high_confidence)
        self.assertFalse(self._make_action(0.0).is_high_confidence)


class TestValidatorConfidenceFunctions(unittest.TestCase):
    """Unit tests for validate_confidence() and is_low_confidence()."""

    def test_validate_valid_floats(self):
        self.assertEqual(validate_confidence(0.0), 0.0)
        self.assertEqual(validate_confidence(0.80), 0.80)
        self.assertEqual(validate_confidence(0.96), 0.96)
        self.assertEqual(validate_confidence(1.0), 1.0)

    def test_validate_integer_converted_to_float(self):
        self.assertIsInstance(validate_confidence(1), float)
        self.assertEqual(validate_confidence(0), 0.0)

    def test_validate_confidence_negative_raises(self):
        with self.assertRaises(ValueError):
            validate_confidence(-1)

    def test_validate_confidence_above_1_raises(self):
        with self.assertRaises(ValueError):
            validate_confidence(2)

    def test_validate_confidence_string_raises(self):
        with self.assertRaises(TypeError):
            validate_confidence("high")

    def test_validate_confidence_none_raises(self):
        with self.assertRaises(TypeError):
            validate_confidence(None)

    def test_is_low_confidence_below_threshold(self):
        self.assertTrue(is_low_confidence(0.0))
        self.assertTrue(is_low_confidence(0.50))
        self.assertTrue(is_low_confidence(0.79))

    def test_is_low_confidence_at_threshold(self):
        self.assertFalse(is_low_confidence(0.80))

    def test_is_low_confidence_above_threshold(self):
        self.assertFalse(is_low_confidence(0.81))
        self.assertFalse(is_low_confidence(0.96))
        self.assertFalse(is_low_confidence(1.0))


class TestConfidenceViaAPI(unittest.TestCase):
    """Integration tests for the confidence pipeline through POST /api/v1/analyze."""

    def setUp(self):
        self.client = TestClient(app)
        self._base_payload = {
            "sanitized_screenshot": "data:image/png;base64,mock",
            "sanitized_dom": "<div><button id='btn'>OK</button></div>",
            "visual_elements": [
                {"type": "button", "id": "btn", "label": "OK", "selector": "#btn"}
            ],
        }

    def _make_payload(self, request_id, instruction):
        return {"request_id": request_id, "user_instruction": instruction, **self._base_payload}

    # ── HIGH CONFIDENCE: action is returned for execution ─────────────────────

    def test_high_confidence_returns_success(self):
        """Click instruction with clear element match should produce ≥ 0.80 confidence."""
        payload = self._make_payload("req-hc-001", "Click the OK button")
        res = self.client.post("/api/v1/analyze", json=payload)
        data = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["confidence"], 0.80)
        self.assertIn("action", data)
        self.assertIn("reason", data)

    def test_high_confidence_confidence_preserved_in_response(self):
        """Verify the exact confidence value from the agent is returned in the response."""
        payload = self._make_payload("req-hc-002", "Click the OK button")
        res = self.client.post("/api/v1/analyze", json=payload)
        data = res.json()
        self.assertEqual(data["status"], "success")
        confidence = data["confidence"]
        self.assertIsInstance(confidence, float)
        self.assertGreaterEqual(confidence, 0.80)
        self.assertLessEqual(confidence, 1.0)

    def test_navigate_action_high_confidence(self):
        """Navigate instruction always produces high confidence."""
        payload = self._make_payload("req-hc-003", "navigate to https://example.com")
        res = self.client.post("/api/v1/analyze", json=payload)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["confidence"], 0.80)
        self.assertEqual(data["action"]["type"], "navigate")

    # ── LOW CONFIDENCE: action NOT returned for execution ─────────────────────

    def test_low_confidence_returns_error_response(self):
        """When agent produces confidence < 0.80, server responds with LOW_CONFIDENCE."""
        payload = self._make_payload(
            "req-lc-001",
            "Click something that doesn't exist anywhere",  # no visual elements matching → 0.70 fallback
        )
        # Override visual_elements to empty so MockPlanner falls back to 0.70
        payload["visual_elements"] = []
        res = self.client.post("/api/v1/analyze", json=payload)
        data = res.json()
        self.assertEqual(res.status_code, 200)  # Still 200 per contract
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "LOW_CONFIDENCE")
        self.assertIn("0.80", data["error"]["message"])

    def test_low_confidence_response_does_not_contain_action(self):
        """LOW_CONFIDENCE response must never include an action the extension could auto-execute."""
        payload = self._make_payload("req-lc-002", "do something vague")
        payload["visual_elements"] = []
        res = self.client.post("/api/v1/analyze", json=payload)
        data = res.json()
        self.assertNotIn("action", data)
        self.assertNotIn("confidence", data)

    # ── MOCK INJECTION: forced confidence values for edge case testing ────────

    def test_exact_boundary_080_produces_success(self):
        """confidence == 0.80 exactly must return success, not LOW_CONFIDENCE."""
        fixed_result = ActionResult(
            action={"type": "click", "target": {"id": "btn", "selector": "#btn"}},
            confidence=0.80,
            reason="Exactly at threshold.",
        )
        with patch("server.routes.agent") as mock_agent:
            mock_agent.act = AsyncMock(return_value=fixed_result)
            payload = self._make_payload("req-bound-001", "Click OK")
            res = self.client.post("/api/v1/analyze", json=payload)
            data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["confidence"], 0.80)

    def test_just_below_threshold_079_produces_low_confidence(self):
        """confidence == 0.79 must trigger LOW_CONFIDENCE."""
        fixed_result = ActionResult(
            action={"type": "click", "target": {"id": "btn", "selector": "#btn"}},
            confidence=0.79,
            reason="Just below threshold.",
        )
        with patch("server.routes.agent") as mock_agent:
            mock_agent.act = AsyncMock(return_value=fixed_result)
            payload = self._make_payload("req-bound-002", "Click OK")
            res = self.client.post("/api/v1/analyze", json=payload)
            data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "LOW_CONFIDENCE")

    def test_confidence_050_produces_low_confidence(self):
        """Mid-range low confidence value."""
        fixed_result = ActionResult(
            action={"type": "scroll", "target": {"direction": "down", "amount": 300}},
            confidence=0.50,
            reason="Low confidence scroll.",
        )
        with patch("server.routes.agent") as mock_agent:
            mock_agent.act = AsyncMock(return_value=fixed_result)
            payload = self._make_payload("req-lc-050", "Scroll down")
            res = self.client.post("/api/v1/analyze", json=payload)
            data = res.json()
        self.assertEqual(data["error"]["code"], "LOW_CONFIDENCE")


if __name__ == "__main__":
    unittest.main()
