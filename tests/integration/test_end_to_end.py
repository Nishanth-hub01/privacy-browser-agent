"""End-to-End Test Suite for Privacy-Preserving Vision Browser Agent.

Tests the complete end-to-end pipeline specified in shared/API_CONTRACT.md:
  Browser Extension
  → Local Privacy Module
  → Sanitized Screenshot + DOM
  → FastAPI Server (POST /api/v1/analyze)
  → AI Agent Planning
  → Action Validation
  → Confidence Check
  → Action JSON Response
  → Browser Extension Execution

Verifies that:
  1. Raw private data is not sent to the server.
  2. Sanitized data reaches the server.
  3. The server validates the request.
  4. The agent generates an action.
  5. The action is validated.
  6. Confidence is checked.
  7. The final action JSON follows API_CONTRACT.md.
"""
import re
import sys
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from server.api import app
from server.privacy_interface import (
    SanitizedContext,
    verify_sanitized_context,
)
from agent import BrowserAgent
import server.routes


# ─── Mock Browser Environment & Extension Simulation ─────────────────────────

@dataclass
class SimulatedDOMElement:
    tag: str
    id: Optional[str] = None
    selector: Optional[str] = None
    classes: List[str] = field(default_factory=list)
    text: str = ""
    value: str = ""
    attributes: Dict[str, str] = field(default_factory=dict)
    x: float = 0.0
    y: float = 0.0
    clicked: bool = False
    typed_text: str = ""


class SimulatedBrowserTab:
    """Simulates a browser webpage DOM and layout for end-to-end testing."""

    def __init__(self, raw_html: str, elements: List[SimulatedDOMElement], url: str):
        self.url = url
        self.raw_html = raw_html
        self.elements = elements
        self.scroll_y = 0

    def capture_screenshot(self) -> str:
        # Returns raw base64 image representation
        return (
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
            "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

    def extract_dom(self) -> str:
        return self.raw_html

    def click_element(self, locator: Dict[str, Any]) -> bool:
        """Simulates extension DOM click execution."""
        target_id = locator.get("id")
        target_sel = locator.get("selector")
        target_x = locator.get("x")
        target_y = locator.get("y")

        for el in self.elements:
            if target_id and el.id == target_id:
                el.clicked = True
                return True
            if target_sel and el.selector == target_sel:
                el.clicked = True
                return True
            if target_x is not None and target_y is not None:
                if abs(el.x - target_x) < 50 and abs(el.y - target_y) < 50:
                    el.clicked = True
                    return True
        return False

    def scroll(self, direction: str, amount: int) -> None:
        """Simulates extension window.scrollBy execution."""
        if direction == "down":
            self.scroll_y += amount
        elif direction == "up":
            self.scroll_y = max(0, self.scroll_y - amount)

    def type_text(self, locator: Dict[str, Any], text: str) -> bool:
        """Simulates extension input value setting and event dispatch."""
        target_id = locator.get("id")
        target_sel = locator.get("selector")
        for el in self.elements:
            if (target_id and el.id == target_id) or (target_sel and el.selector == target_sel):
                el.value = text
                el.typed_text = text
                return True
        return False

    def navigate(self, url: str) -> None:
        """Simulates extension window.location.href navigation."""
        self.url = url


class SimulatedLocalPrivacyModule:
    """Simulates Member 2's local privacy detection, redaction, and verification."""

    @staticmethod
    def process(
        request_id: str,
        user_instruction: str,
        raw_screenshot: str,
        raw_dom: str,
        raw_elements: List[SimulatedDOMElement],
    ) -> SanitizedContext:
        # 1. Detect and redact sensitive PII patterns
        sanitized_dom = raw_dom

        # Redact passwords
        sanitized_dom = re.sub(
            r"(?i)\b(password\s*[:=]\s*)([^\s\"'<>,;]+)",
            r"\1[REDACTED]",
            sanitized_dom,
        )
        # Redact emails
        sanitized_dom = re.sub(
            r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
            "[EMAIL]",
            sanitized_dom,
        )
        # Redact card numbers
        sanitized_dom = re.sub(
            r"\b(?:\d{4}[- ]?){3}\d{4}\b",
            "[CARD]",
            sanitized_dom,
        )
        # Redact phone numbers
        sanitized_dom = re.sub(
            r"\+\d[\d\s\-().]{7,}\d",
            "[PHONE]",
            sanitized_dom,
        )
        # Redact names
        sanitized_dom = re.sub(
            r"John Smith|Fake Person|Jane Doe",
            "[PERSON]",
            sanitized_dom,
        )

        # 2. Redact screenshot (simulated by returning redacted image)
        sanitized_screenshot = raw_screenshot.replace("mock", "sanitized_blurred")

        # 3. Extract safe visual elements (no sensitive values)
        safe_visual_elements = []
        for el in raw_elements:
            safe_el = {
                "type": el.tag,
                "id": el.id,
                "selector": el.selector,
                "label": el.text,
                "x": el.x,
                "y": el.y,
            }
            # Ensure no raw passwords in attributes
            if "password" in el.value.lower():
                safe_el["value"] = "[REDACTED]"
            safe_visual_elements.append(safe_el)

        context = SanitizedContext(
            request_id=request_id,
            user_instruction=user_instruction,
            sanitized_screenshot=sanitized_screenshot,
            sanitized_dom=sanitized_dom,
            visual_elements=safe_visual_elements,
        )

        # 4. Privacy verification
        violation = verify_sanitized_context(context)
        if violation:
            raise ValueError(f"Privacy verification failed: {violation}")

        return context


# ─── End-to-End Test Suite ───────────────────────────────────────────────────

class TestEndToEndPrivacyBrowserAgent(unittest.TestCase):
    """Exhaustive tests covering the full end-to-end pipeline."""

    def setUp(self):
        self.client = TestClient(app)
        server.routes.agent = BrowserAgent()

    # ── E2E Test 1: Complete INT-019 Click Scenario ───────────────────────────

    def test_e2e_int_019_upload_document_click_flow(self):
        """Test INT-019: Webpage with sensitive user info + Upload button.

        Complete Step-by-Step Flow:
          1. Extension captures webpage (contains Name, Email, Password, [Upload Document], [Submit]).
          2. Privacy module detects & redacts PII/passwords.
          3. Privacy module verifies sanitized context.
          4. Extension sends sanitized context ONLY to FastAPI server.
          5. Server PII guard confirms zero raw private data.
          6. Server validates request schema and context integrity.
          7. AI Agent plans action on sanitized data.
          8. Server validates action schema and checks confidence (>= 0.80).
          9. Server returns action JSON matching API_CONTRACT.md.
          10. Extension validates action JSON and executes click on Upload Document.
        """
        # Step 1: Raw webpage setup in browser tab
        raw_dom = (
            "<div class='profile-card'>"
            "  <h2>User Profile</h2>"
            "  <p>Name: Fake Person</p>"
            "  <p>Email: test@example.com</p>"
            "  <p>Password: FakePassword123</p>"
            "  <button id='upload-btn' class='btn-secondary'>Upload Document</button>"
            "  <button id='submit-btn' class='btn-primary'>Submit</button>"
            "</div>"
        )
        upload_btn = SimulatedDOMElement(
            tag="button",
            id="upload-btn",
            selector="#upload-btn",
            text="Upload Document",
            x=450.0,
            y=350.0,
        )
        submit_btn = SimulatedDOMElement(
            tag="button",
            id="submit-btn",
            selector="#submit-btn",
            text="Submit",
            x=450.0,
            y=450.0,
        )
        browser_tab = SimulatedBrowserTab(
            raw_html=raw_dom,
            elements=[upload_btn, submit_btn],
            url="https://example.com/account",
        )

        request_id = "e2e-req-001"
        user_instruction = "Find the upload button"

        # Step 2: Extension extracts raw screenshot and DOM
        raw_screenshot = browser_tab.capture_screenshot()
        extracted_dom = browser_tab.extract_dom()

        # Step 3: Local Privacy module detects, redacts, and verifies
        sanitized_context = SimulatedLocalPrivacyModule.process(
            request_id=request_id,
            user_instruction=user_instruction,
            raw_screenshot=raw_screenshot,
            raw_dom=extracted_dom,
            raw_elements=[upload_btn, submit_btn],
        )

        # Verification 1: Confirm raw private data was eliminated before server
        self.assertNotIn("Fake Person", sanitized_context.sanitized_dom)
        self.assertNotIn("test@example.com", sanitized_context.sanitized_dom)
        self.assertNotIn("FakePassword123", sanitized_context.sanitized_dom)
        self.assertIn("[PERSON]", sanitized_context.sanitized_dom)
        self.assertIn("[EMAIL]", sanitized_context.sanitized_dom)
        self.assertIn("[REDACTED]", sanitized_context.sanitized_dom)

        # Step 4: Extension sends sanitized payload to FastAPI Server
        server_payload = {
            "request_id": sanitized_context.request_id,
            "user_instruction": sanitized_context.user_instruction,
            "sanitized_screenshot": sanitized_context.sanitized_screenshot,
            "sanitized_dom": sanitized_context.sanitized_dom,
            "visual_elements": sanitized_context.visual_elements,
        }
        # Verify prohibited raw fields are NEVER present
        self.assertNotIn("screenshot", server_payload)
        self.assertNotIn("dom", server_payload)

        # Step 5: Server processing
        http_response = self.client.post("/api/v1/analyze", json=server_payload)

        # Verification 2 & 3: Server HTTP status & validation
        self.assertEqual(http_response.status_code, 200)
        response_json = http_response.json()

        # Verification 4 & 5 & 6 & 7: Check API Contract fields & action
        self.assertEqual(response_json["request_id"], request_id)
        self.assertEqual(response_json["status"], "success")
        self.assertIn("action", response_json)
        self.assertIn("confidence", response_json)
        self.assertIn("reason", response_json)

        action = response_json["action"]
        self.assertEqual(action["type"], "click")
        self.assertEqual(action["target"]["id"], "upload-btn")
        self.assertGreaterEqual(response_json["confidence"], 0.80)
        self.assertIn("Upload Document", response_json["reason"])

        # Step 6: Extension receives action and executes it
        execution_success = browser_tab.click_element(action["target"])
        self.assertTrue(execution_success)
        self.assertTrue(upload_btn.clicked, "Upload Document button must be clicked!")
        self.assertFalse(submit_btn.clicked, "Submit button must NOT be clicked!")

    # ── E2E Test 2: Scroll Action Flow ────────────────────────────────────────

    def test_e2e_scroll_action_flow(self):
        """Test complete scroll flow from extension request to browser scrolling."""
        raw_dom = "<div class='content'>Articles list</div>"
        browser_tab = SimulatedBrowserTab(
            raw_html=raw_dom,
            elements=[],
            url="https://example.com/news",
        )

        request_id = "e2e-req-scroll-002"
        user_instruction = "Scroll down 600px to see more articles"

        sanitized_context = SimulatedLocalPrivacyModule.process(
            request_id=request_id,
            user_instruction=user_instruction,
            raw_screenshot=browser_tab.capture_screenshot(),
            raw_dom=browser_tab.extract_dom(),
            raw_elements=[],
        )

        server_payload = {
            "request_id": sanitized_context.request_id,
            "user_instruction": sanitized_context.user_instruction,
            "sanitized_screenshot": sanitized_context.sanitized_screenshot,
            "sanitized_dom": sanitized_context.sanitized_dom,
            "visual_elements": sanitized_context.visual_elements,
        }

        res = self.client.post("/api/v1/analyze", json=server_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"]["type"], "scroll")
        self.assertEqual(data["action"]["target"]["direction"], "down")
        self.assertEqual(data["action"]["target"]["amount"], 600)
        self.assertGreaterEqual(data["confidence"], 0.80)

        # Extension executes scroll
        browser_tab.scroll(
            data["action"]["target"]["direction"],
            data["action"]["target"]["amount"],
        )
        self.assertEqual(browser_tab.scroll_y, 600)

    # ── E2E Test 3: Type Action Flow ──────────────────────────────────────────

    def test_e2e_type_action_flow(self):
        """Test complete type flow from user typing intent to input field value update."""
        raw_dom = (
            "<div class='search-container'>"
            "  <input id='search-input' type='text' placeholder='Search knowledge base' />"
            "</div>"
        )
        search_input = SimulatedDOMElement(
            tag="input",
            id="search-input",
            selector="#search-input",
            text="Search knowledge base",
            x=200.0,
            y=100.0,
        )
        browser_tab = SimulatedBrowserTab(
            raw_html=raw_dom,
            elements=[search_input],
            url="https://example.com/help",
        )

        request_id = "e2e-req-type-003"
        user_instruction = "type 'privacy guidelines' into search"

        sanitized_context = SimulatedLocalPrivacyModule.process(
            request_id=request_id,
            user_instruction=user_instruction,
            raw_screenshot=browser_tab.capture_screenshot(),
            raw_dom=browser_tab.extract_dom(),
            raw_elements=[search_input],
        )

        server_payload = {
            "request_id": sanitized_context.request_id,
            "user_instruction": sanitized_context.user_instruction,
            "sanitized_screenshot": sanitized_context.sanitized_screenshot,
            "sanitized_dom": sanitized_context.sanitized_dom,
            "visual_elements": sanitized_context.visual_elements,
        }

        res = self.client.post("/api/v1/analyze", json=server_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"]["type"], "type")
        self.assertEqual(data["action"]["text"], "privacy guidelines")
        self.assertEqual(data["action"]["target"]["id"], "search-input")

        # Extension executes typing
        type_success = browser_tab.type_text(
            data["action"]["target"],
            data["action"]["text"],
        )
        self.assertTrue(type_success)
        self.assertEqual(search_input.value, "privacy guidelines")

    # ── E2E Test 4: Navigate Action Flow ──────────────────────────────────────

    def test_e2e_navigate_action_flow(self):
        """Test complete navigation flow from URL intent to browser tab navigation."""
        browser_tab = SimulatedBrowserTab(
            raw_html="<div>Dashboard</div>",
            elements=[],
            url="https://example.com/home",
        )

        request_id = "e2e-req-nav-004"
        user_instruction = "navigate to https://example.com/settings"

        sanitized_context = SimulatedLocalPrivacyModule.process(
            request_id=request_id,
            user_instruction=user_instruction,
            raw_screenshot=browser_tab.capture_screenshot(),
            raw_dom=browser_tab.extract_dom(),
            raw_elements=[],
        )

        server_payload = {
            "request_id": sanitized_context.request_id,
            "user_instruction": sanitized_context.user_instruction,
            "sanitized_screenshot": sanitized_context.sanitized_screenshot,
            "sanitized_dom": sanitized_context.sanitized_dom,
            "visual_elements": sanitized_context.visual_elements,
        }

        res = self.client.post("/api/v1/analyze", json=server_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"]["type"], "navigate")
        self.assertEqual(data["action"]["target"]["url"], "https://example.com/settings")

        # Extension executes navigation
        browser_tab.navigate(data["action"]["target"]["url"])
        self.assertEqual(browser_tab.url, "https://example.com/settings")

    # ── E2E Test 5: Privacy Boundary Security Enforcement ─────────────────────

    def test_e2e_privacy_boundary_blocks_unsanitized_transmission(self):
        """Test INT-004 & INT-015: If unsanitized data attempts to reach the server,

        the server's last-resort privacy guard blocks it immediately with HTTP 400.
        """
        raw_dom_with_password = "<div>Password: SecretAdminPassword999</div>"
        leaked_payload = {
            "request_id": "e2e-req-leak-005",
            "user_instruction": "Log into admin panel",
            "sanitized_screenshot": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "sanitized_dom": raw_dom_with_password,  # Leaked unredacted password!
            "visual_elements": [],
        }

        # Server MUST reject this
        res = self.client.post("/api/v1/analyze", json=leaked_payload)
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "PRIVACY_CHECK_FAILED")
        self.assertIn("raw_password", data["error"]["message"])

    # ── E2E Test 6: Low Confidence Safety Protection ──────────────────────────

    def test_e2e_low_confidence_prevents_automatic_execution(self):
        """Test INT-013: AI returns confidence < 0.80; extension must NOT execute."""
        ambiguous_payload = {
            "request_id": "e2e-req-lowconf-006",
            "user_instruction": "Click something that does not exist anywhere",
            "sanitized_screenshot": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "sanitized_dom": "<div>Simple page with no buttons</div>",
            "visual_elements": [],
        }

        res = self.client.post("/api/v1/analyze", json=ambiguous_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Contract verification: status is error, error code is LOW_CONFIDENCE
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "LOW_CONFIDENCE")
        self.assertIn("0.80", data["error"]["message"])
        self.assertNotIn("action", data)


if __name__ == "__main__":
    unittest.main()
