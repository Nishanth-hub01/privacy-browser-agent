"""Comprehensive unit tests for Server API endpoints, Agent Planner, and Pipeline validation."""
import unittest
import sys
from pathlib import Path

# Ensure paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from server.api import app
from agent import BrowserAgent, AgentContext
from agent.actions import ActionResult
from server.validator import validate_browser_action, check_privacy_violations
from server.schemas import AnalyzeRequest, ErrorCode


class TestServerAndAgentPipeline(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.agent = BrowserAgent()

    def test_health_endpoint(self):
        """Verify root health check endpoint returns running status."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "running")

    def test_click_action_via_api(self):
        """Test click action planning from valid request."""
        payload = {
            "request_id": "req-click-001",
            "user_instruction": "Click the Submit button",
            "sanitized_screenshot": "data:image/png;base64,mock",
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
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"]["type"], "click")
        self.assertEqual(data["action"]["target"]["id"], "submit-btn")
        self.assertGreaterEqual(data["confidence"], 0.80)

    def test_scroll_action_via_api(self):
        """Test scroll action planning from valid request."""
        payload = {
            "request_id": "req-scroll-001",
            "user_instruction": "Scroll down 400px",
            "sanitized_screenshot": "data:image/png;base64,mock",
            "sanitized_dom": "<div>content</div>",
            "visual_elements": [],
        }
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"]["type"], "scroll")
        self.assertEqual(data["action"]["target"]["direction"], "down")
        self.assertEqual(data["action"]["target"]["amount"], 400)

    def test_type_action_via_api(self):
        """Test type action planning from valid request."""
        payload = {
            "request_id": "req-type-001",
            "user_instruction": "type 'hello world' into search",
            "sanitized_screenshot": "data:image/png;base64,mock",
            "sanitized_dom": "<input id='search-box' type='text'/>",
            "visual_elements": [
                {"type": "input", "id": "search-box", "selector": "#search-box"}
            ],
        }
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"]["type"], "type")
        self.assertEqual(data["action"]["text"], "hello world")
        self.assertEqual(data["action"]["target"]["id"], "search-box")

    def test_navigate_action_via_api(self):
        """Test navigate action planning from valid request."""
        payload = {
            "request_id": "req-nav-001",
            "user_instruction": "navigate to https://example.com/login",
            "sanitized_screenshot": "data:image/png;base64,mock",
            "sanitized_dom": "",
            "visual_elements": [],
        }
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"]["type"], "navigate")
        self.assertEqual(data["action"]["target"]["url"], "https://example.com/login")

    def test_privacy_boundary_rejection(self):
        """Verify request containing raw password is rejected with PRIVACY_CHECK_FAILED."""
        payload = {
            "request_id": "req-priv-001",
            "user_instruction": "Login to the portal",
            "sanitized_screenshot": "data:image/png;base64,mock",
            "sanitized_dom": "<div>Password: FakePassword123</div>",
            "visual_elements": [],
        }
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "PRIVACY_CHECK_FAILED")

    def test_low_confidence_handling(self):
        """Verify request with low confidence returns LOW_CONFIDENCE error response."""
        payload = {
            "request_id": "req-low-conf-001",
            "user_instruction": "Click something that doesn't exist anywhere",
            "sanitized_screenshot": "data:image/png;base64,mock",
            "sanitized_dom": "<div>empty</div>",
            "visual_elements": [],
        }
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "LOW_CONFIDENCE")

    def test_invalid_request_missing_fields(self):
        """Verify missing required fields return INVALID_REQUEST error."""
        payload = {"request_id": "req-bad"}
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "INVALID_REQUEST")

    def test_action_validator_unit(self):
        """Unit test for validate_browser_action helper."""
        # Unsupported action
        with self.assertRaises(ValueError):
            validate_browser_action({"type": "delete_all"})

        # Missing target for click
        with self.assertRaises(Exception):
            validate_browser_action({"type": "click"})

        # Invalid scroll direction
        with self.assertRaises(Exception):
            validate_browser_action({"type": "scroll", "target": {"direction": "sideways", "amount": 100}})


if __name__ == "__main__":
    unittest.main()
