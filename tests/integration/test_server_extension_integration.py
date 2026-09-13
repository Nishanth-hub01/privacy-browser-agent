"""Integration tests for Server-to-Extension communication.

Verifies the complete Server -> Extension contract defined in shared/API_CONTRACT.md:
  1. Response contains all 5 required fields:
     - request_id
     - status
     - action
     - confidence
     - reason
  2. Action formats are suitable for browser extension execution:
     - click: target with id/selector/coordinates executable via DOM click
     - scroll: target with direction ('up'|'down') and positive amount executable via window.scrollBy
     - type: target with element identifier + text string executable via input dispatch
     - navigate: target with validated URL executable via window.location / chrome.tabs
  3. Realistic sanitized browser data containing privacy redaction tokens:
     - [PERSON], [EMAIL], [CARD], [REDACTED], [PHONE]
  4. Low confidence handling (< 0.80) signals extension to pause auto-execution
  5. Privacy guard rejection and error envelope consistency
"""
import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from server.api import app
from agent import BrowserAgent
import server.routes


# Realistic 1x1 transparent PNG base64 for sanitized screenshot
REALISTIC_SANITIZED_SCREENSHOT = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


class TestServerToExtensionIntegration(unittest.TestCase):
    """End-to-End integration test suite for Server-to-Extension contract."""

    def setUp(self):
        self.client = TestClient(app)
        # Ensure standard agent instance is active
        server.routes.agent = BrowserAgent()

    # ── 1. Contract Fields & Click Action ─────────────────────────────────────

    def test_click_action_contains_all_five_required_fields(self):
        """Verify response contains request_id, status, action, confidence, reason

        and that the click action is directly executable by the browser extension.
        """
        payload = {
            "request_id": "ext-req-click-001",
            "user_instruction": "Click the Proceed to Checkout button",
            "sanitized_screenshot": REALISTIC_SANITIZED_SCREENSHOT,
            "sanitized_dom": (
                "<div class='cart-summary'>"
                "  <div class='customer-info'>Name: [PERSON], Email: [EMAIL]</div>"
                "  <button id='checkout-btn' class='btn-primary' "
                "          style='width:200px;height:45px;'>Proceed to Checkout</button>"
                "</div>"
            ),
            "visual_elements": [
                {
                    "type": "button",
                    "label": "Proceed to Checkout",
                    "id": "checkout-btn",
                    "selector": "#checkout-btn",
                    "x": 520.0,
                    "y": 410.0,
                    "width": 200.0,
                    "height": 45.0,
                }
            ],
        }

        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # 1. Verify all 5 top-level contract fields
        self.assertIn("request_id", data)
        self.assertIn("status", data)
        self.assertIn("action", data)
        self.assertIn("confidence", data)
        self.assertIn("reason", data)

        # 2. Check field values and types
        self.assertEqual(data["request_id"], "ext-req-click-001")
        self.assertEqual(data["status"], "success")
        self.assertIsInstance(data["confidence"], (int, float))
        self.assertGreaterEqual(data["confidence"], 0.80)
        self.assertLessEqual(data["confidence"], 1.0)
        self.assertIsInstance(data["reason"], str)
        self.assertTrue(len(data["reason"].strip()) > 0)

        # 3. Action format suitability for browser extension
        action = data["action"]
        self.assertEqual(action["type"], "click")
        self.assertIn("target", action)
        target = action["target"]
        self.assertIsInstance(target, dict)
        # Extension can locate element by id or selector or coordinates
        has_id = bool(target.get("id"))
        has_selector = bool(target.get("selector"))
        has_coords = target.get("x") is not None and target.get("y") is not None
        self.assertTrue(
            has_id or has_selector or has_coords,
            "Click target must contain at least one valid locator for extension execution",
        )
        self.assertEqual(target.get("id"), "checkout-btn")

    # ── 2. Scroll Action Suitability ──────────────────────────────────────────

    def test_scroll_action_suitability_for_extension(self):
        """Verify scroll action returns direction and pixel amount for window.scrollBy."""
        payload = {
            "request_id": "ext-req-scroll-002",
            "user_instruction": "Scroll down 750px to read user reviews",
            "sanitized_screenshot": REALISTIC_SANITIZED_SCREENSHOT,
            "sanitized_dom": (
                "<div class='product-page'>"
                "  <section class='details'>Description here</section>"
                "  <section class='reviews'>Customer reviews: [PERSON] says great product</section>"
                "</div>"
            ),
            "visual_elements": [],
        }

        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check required fields
        self.assertEqual(data["request_id"], "ext-req-scroll-002")
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["confidence"], 0.80)
        self.assertIsInstance(data["reason"], str)

        # Action suitability: direction in ('up', 'down') and positive integer amount
        action = data["action"]
        self.assertEqual(action["type"], "scroll")
        self.assertIn("target", action)
        target = action["target"]
        self.assertIn(target["direction"], ("up", "down"))
        self.assertEqual(target["direction"], "down")
        self.assertIsInstance(target["amount"], int)
        self.assertEqual(target["amount"], 750)
        self.assertGreater(target["amount"], 0)

    # ── 3. Type Action Suitability ────────────────────────────────────────────

    def test_type_action_suitability_for_extension(self):
        """Verify type action returns target locator and text for extension input dispatch."""
        payload = {
            "request_id": "ext-req-type-003",
            "user_instruction": "type 'privacy preserving agent' into search",
            "sanitized_screenshot": REALISTIC_SANITIZED_SCREENSHOT,
            "sanitized_dom": (
                "<nav class='search-bar'>"
                "  <input id='global-search' name='q' type='text' placeholder='Search...' />"
                "  <button id='search-btn'>Search</button>"
                "</nav>"
            ),
            "visual_elements": [
                {
                    "type": "input",
                    "id": "global-search",
                    "selector": "#global-search",
                    "label": "Search...",
                    "x": 200.0,
                    "y": 50.0,
                },
                {
                    "type": "button",
                    "id": "search-btn",
                    "selector": "#search-btn",
                    "label": "Search",
                },
            ],
        }

        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check required fields
        self.assertEqual(data["request_id"], "ext-req-type-003")
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["confidence"], 0.80)

        # Action suitability: target with locator and text string to type
        action = data["action"]
        self.assertEqual(action["type"], "type")
        self.assertIn("target", action)
        self.assertIn("text", action)
        self.assertEqual(action["text"], "privacy preserving agent")
        self.assertEqual(action["target"].get("id"), "global-search")

    # ── 4. Navigate Action Suitability ────────────────────────────────────────

    def test_navigate_action_suitability_for_extension(self):
        """Verify navigate action returns valid URL for chrome.tabs.update / window.location."""
        payload = {
            "request_id": "ext-req-nav-004",
            "user_instruction": "navigate to https://github.com/settings/profile",
            "sanitized_screenshot": REALISTIC_SANITIZED_SCREENSHOT,
            "sanitized_dom": "<div class='profile-page'>Current: [PERSON]</div>",
            "visual_elements": [],
        }

        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check required fields
        self.assertEqual(data["request_id"], "ext-req-nav-004")
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["confidence"], 0.80)

        # Action suitability: target.url is a valid URL
        action = data["action"]
        self.assertEqual(action["type"], "navigate")
        self.assertIn("target", action)
        self.assertTrue(action["target"]["url"].startswith("https://"))
        self.assertEqual(action["target"]["url"], "https://github.com/settings/profile")

    # ── 5. Realistic Sanitized Browser Data with Redaction Tokens ─────────────

    def test_realistic_sanitized_browser_data_with_tokens(self):
        """Verify server successfully handles realistic DOM with [PERSON], [EMAIL], [CARD], [REDACTED]."""
        payload = {
            "request_id": "ext-req-sanitized-005",
            "user_instruction": "Click the Save Changes button",
            "sanitized_screenshot": REALISTIC_SANITIZED_SCREENSHOT,
            "sanitized_dom": (
                "<form id='account-form'>"
                "  <div class='field'><label>Name</label><input value='[PERSON]' disabled /></div>"
                "  <div class='field'><label>Email</label><input value='[EMAIL]' disabled /></div>"
                "  <div class='field'><label>Phone</label><input value='[PHONE]' disabled /></div>"
                "  <div class='field'><label>Card</label><input value='Card ending in [CARD]' disabled /></div>"
                "  <div class='field'><label>Password</label><input type='password' value='[REDACTED]' /></div>"
                "  <button id='save-btn' type='submit'>Save Changes</button>"
                "</form>"
            ),
            "visual_elements": [
                {
                    "type": "button",
                    "label": "Save Changes",
                    "id": "save-btn",
                    "selector": "#save-btn",
                    "x": 300.0,
                    "y": 600.0,
                    "width": 160.0,
                    "height": 40.0,
                }
            ],
        }

        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["status"], "success")
        self.assertEqual(data["request_id"], "ext-req-sanitized-005")
        self.assertEqual(data["action"]["type"], "click")
        self.assertEqual(data["action"]["target"]["id"], "save-btn")
        self.assertGreaterEqual(data["confidence"], 0.80)

    # ── 6. Low Confidence Safety Contract ────────────────────────────────────

    def test_low_confidence_action_contract_for_extension(self):
        """Verify low-confidence action returns status: 'error' and code: 'LOW_CONFIDENCE'.

        The extension MUST NOT automatically execute actions when confidence < 0.80.
        """
        payload = {
            "request_id": "ext-req-lowconf-006",
            "user_instruction": "Click the invisible mysterious teleport link",
            "sanitized_screenshot": REALISTIC_SANITIZED_SCREENSHOT,
            "sanitized_dom": "<div>Page contains no such element</div>",
            "visual_elements": [],
        }

        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["request_id"], "ext-req-lowconf-006")
        self.assertEqual(data["status"], "error")
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "LOW_CONFIDENCE")
        self.assertIn("0.80", data["error"]["message"])
        # Crucial for extension: 'action' key must not be present in error response
        self.assertNotIn("action", data)

    # ── 7. Privacy Boundary Rejection ─────────────────────────────────────────

    def test_privacy_boundary_rejects_unsanitized_payload(self):
        """Verify server rejects unsanitized raw password with HTTP 400 PRIVACY_CHECK_FAILED."""
        payload = {
            "request_id": "ext-req-priv-007",
            "user_instruction": "Submit credentials",
            "sanitized_screenshot": REALISTIC_SANITIZED_SCREENSHOT,
            "sanitized_dom": (
                "<form>"
                "  <input name='password' value='password: PlainTextPassword123' />"
                "  <button id='submit-btn'>Submit</button>"
                "</form>"
            ),
            "visual_elements": [{"type": "button", "id": "submit-btn"}],
        }

        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.json()

        self.assertEqual(data["request_id"], "ext-req-priv-007")
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "PRIVACY_CHECK_FAILED")


if __name__ == "__main__":
    unittest.main()
