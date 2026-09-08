"""Integration readiness tests: sanitized context acceptance and raw data rejection.

Tests per API_CONTRACT.md §3 (privacy rule) and §6 (Privacy→Server payload):

Sanitized input (must be accepted):
  - sanitized_screenshot  — base64-encoded, redacted image
  - sanitized_dom         — HTML with PII tokens ([REDACTED], [EMAIL], etc.)
  - visual_elements       — safe element descriptor list
  - user_instruction      — natural-language instruction

Raw / unsanitized input (must be rejected):
  - Unredacted passwords in dom or instruction
  - Unredacted email addresses in dom or instruction
  - Unredacted phone numbers in dom or instruction
  - Unredacted card numbers in dom or instruction
  - Empty / missing sanitized_screenshot (INVALID_CONTEXT)
  - Missing required fields (INVALID_REQUEST)

Also verifies:
  - GET /api/v1/privacy-status returns integration status correctly
  - SanitizedContext dataclass and verify_sanitized_context() work correctly
  - privacy_module_is_available() returns False (placeholder-only privacy/)
"""
import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from server.api import app
from server.privacy_interface import (
    SanitizedContext,
    verify_sanitized_context,
    check_sanitized_fields,
    privacy_module_is_available,
    INTEGRATION_STATUS,
)
import server.routes


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _make_clean_payload(**overrides):
    """Return a fully valid, sanitized request payload."""
    base = {
        "request_id": "req-priv-integration-001",
        "user_instruction": "Click the Upload button",
        "sanitized_screenshot": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "sanitized_dom": "<button id='upload-btn'>Upload Document</button>",
        "visual_elements": [
            {"type": "button", "label": "Upload Document", "id": "upload-btn", "selector": "#upload-btn"}
        ],
    }
    base.update(overrides)
    return base


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestSanitizedInputAccepted(unittest.TestCase):
    """Valid sanitized input must be accepted and produce a successful action."""

    def setUp(self):
        self.client = TestClient(app)

    # ── 1. Valid sanitized click action ───────────────────────────────────────

    def test_sanitized_click_input_accepted(self):
        """Fully sanitized payload with button element → HTTP 200 click action."""
        payload = _make_clean_payload(
            user_instruction="Click the Upload button",
            sanitized_dom="<button id='upload-btn'>Upload Document</button>",
            visual_elements=[
                {"type": "button", "label": "Upload Document", "id": "upload-btn", "selector": "#upload-btn"}
            ],
        )
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"]["type"], "click")

    # ── 2. Valid sanitized scroll action ──────────────────────────────────────

    def test_sanitized_scroll_input_accepted(self):
        """Fully sanitized payload with scroll instruction → HTTP 200 scroll action."""
        payload = _make_clean_payload(
            user_instruction="Scroll down 600px",
            sanitized_dom="<div>Long content page</div>",
            visual_elements=[],
        )
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"]["type"], "scroll")

    # ── 3. Valid sanitized type action ────────────────────────────────────────

    def test_sanitized_type_input_accepted(self):
        """Fully sanitized payload with input field → HTTP 200 type action."""
        payload = _make_clean_payload(
            user_instruction="type 'hello' into search",
            sanitized_dom="<input id='search-box' type='text' />",
            visual_elements=[{"type": "input", "id": "search-box", "selector": "#search-box"}],
        )
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"]["type"], "type")

    # ── 4. Valid sanitized navigate action ────────────────────────────────────

    def test_sanitized_navigate_input_accepted(self):
        """Fully sanitized payload with navigate instruction → HTTP 200 navigate action."""
        payload = _make_clean_payload(
            user_instruction="navigate to https://example.com/dashboard",
            sanitized_dom="",
            visual_elements=[],
        )
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"]["type"], "navigate")

    # ── 5. Sanitized DOM with privacy tokens ─────────────────────────────────

    def test_sanitized_dom_with_privacy_tokens_accepted(self):
        """DOM that has already been sanitized (PII replaced with tokens) is accepted."""
        payload = _make_clean_payload(
            user_instruction="Click Submit",
            sanitized_dom=(
                "<form>"
                "<input name='name' value='[PERSON]' />"
                "<input name='email' value='[EMAIL]' />"
                "<input type='password' value='[REDACTED]' />"
                "<button id='submit-btn'>Submit</button>"
                "</form>"
            ),
            visual_elements=[{"type": "button", "id": "submit-btn", "selector": "#submit-btn"}],
        )
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")

    # ── 6. Empty sanitized_dom is allowed for navigation ──────────────────────

    def test_empty_sanitized_dom_allowed_for_navigation(self):
        """Empty sanitized_dom is valid (e.g. for initial navigation from about:blank)."""
        payload = _make_clean_payload(
            user_instruction="navigate to https://example.com",
            sanitized_dom="",
            visual_elements=[],
        )
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertIn(res.json()["status"], ("success", "error"))  # May be low-conf; both are valid


class TestRawDataRejected(unittest.TestCase):
    """Raw/unsanitized private data must be rejected with PRIVACY_CHECK_FAILED."""

    def setUp(self):
        self.client = TestClient(app)

    def _assert_privacy_failed(self, payload):
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "PRIVACY_CHECK_FAILED")
        return data

    # ── Raw passwords ─────────────────────────────────────────────────────────

    def test_raw_password_in_dom_rejected(self):
        """Unredacted password in sanitized_dom → PRIVACY_CHECK_FAILED."""
        payload = _make_clean_payload(
            sanitized_dom="<div>Password: SuperSecret123</div>"
        )
        data = self._assert_privacy_failed(payload)
        self.assertIn("raw_password", data["error"]["message"])

    def test_raw_password_in_instruction_rejected(self):
        """Unredacted password in user_instruction → PRIVACY_CHECK_FAILED."""
        payload = _make_clean_payload(
            user_instruction="Enter password: MyPass9999"
        )
        self._assert_privacy_failed(payload)

    def test_password_with_redacted_token_accepted(self):
        """Password field showing [REDACTED] token is properly sanitized — accepted."""
        payload = _make_clean_payload(
            sanitized_dom="<input type='password' value='[REDACTED]' />"
        )
        res = self.client.post("/api/v1/analyze", json=payload)
        # Must NOT be a PRIVACY_CHECK_FAILED
        data = res.json()
        self.assertNotEqual(data.get("error", {}).get("code"), "PRIVACY_CHECK_FAILED")

    # ── Raw email addresses ───────────────────────────────────────────────────

    def test_raw_email_in_dom_rejected(self):
        """Unredacted email address in sanitized_dom → PRIVACY_CHECK_FAILED."""
        payload = _make_clean_payload(
            sanitized_dom="<div>Contact us at john.doe@example.com for support.</div>"
        )
        data = self._assert_privacy_failed(payload)
        self.assertIn("raw_email", data["error"]["message"])

    def test_raw_email_in_instruction_rejected(self):
        """Unredacted email in user_instruction → PRIVACY_CHECK_FAILED."""
        payload = _make_clean_payload(
            user_instruction="Login using user@example.com"
        )
        self._assert_privacy_failed(payload)

    def test_email_token_accepted(self):
        """DOM with [EMAIL] token is properly sanitized — accepted."""
        payload = _make_clean_payload(
            sanitized_dom="<div>Contact: [EMAIL]</div>"
        )
        res = self.client.post("/api/v1/analyze", json=payload)
        data = res.json()
        self.assertNotEqual(data.get("error", {}).get("code"), "PRIVACY_CHECK_FAILED")

    # ── Raw phone numbers ─────────────────────────────────────────────────────

    def test_raw_phone_in_dom_rejected(self):
        """Unredacted phone number in sanitized_dom → PRIVACY_CHECK_FAILED."""
        payload = _make_clean_payload(
            sanitized_dom="<div>Call us: +1 800 555 0100</div>"
        )
        data = self._assert_privacy_failed(payload)
        self.assertIn("raw_phone", data["error"]["message"])

    def test_phone_token_accepted(self):
        """DOM with [PHONE] token is properly sanitized — accepted."""
        payload = _make_clean_payload(
            sanitized_dom="<div>Phone: [PHONE]</div>"
        )
        res = self.client.post("/api/v1/analyze", json=payload)
        data = res.json()
        self.assertNotEqual(data.get("error", {}).get("code"), "PRIVACY_CHECK_FAILED")

    # ── Raw card numbers ──────────────────────────────────────────────────────

    def test_raw_card_number_in_dom_rejected(self):
        """Unredacted credit card number in sanitized_dom → PRIVACY_CHECK_FAILED."""
        payload = _make_clean_payload(
            sanitized_dom="<div>Card: 4111 1111 1111 1111</div>"
        )
        data = self._assert_privacy_failed(payload)
        self.assertIn("raw_card_number", data["error"]["message"])

    def test_card_token_accepted(self):
        """DOM with [CARD] token is properly sanitized — accepted."""
        payload = _make_clean_payload(
            sanitized_dom="<span>Card ending in [CARD]</span>"
        )
        res = self.client.post("/api/v1/analyze", json=payload)
        data = res.json()
        self.assertNotEqual(data.get("error", {}).get("code"), "PRIVACY_CHECK_FAILED")


class TestInvalidContextRejected(unittest.TestCase):
    """Missing or empty sanitized context fields must return INVALID_CONTEXT or INVALID_REQUEST."""

    def setUp(self):
        self.client = TestClient(app)

    def test_missing_sanitized_screenshot_field(self):
        """Missing sanitized_screenshot field → HTTP 400 INVALID_REQUEST."""
        payload = _make_clean_payload()
        del payload["sanitized_screenshot"]
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"]["code"], "INVALID_REQUEST")

    def test_empty_sanitized_screenshot(self):
        """Empty sanitized_screenshot → HTTP 422 INVALID_CONTEXT."""
        payload = _make_clean_payload(sanitized_screenshot="")
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.json()["error"]["code"], "INVALID_CONTEXT")

    def test_very_short_sanitized_screenshot(self):
        """Implausibly short screenshot (< 10 chars) → HTTP 422 INVALID_CONTEXT."""
        payload = _make_clean_payload(sanitized_screenshot="tiny")
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.json()["error"]["code"], "INVALID_CONTEXT")

    def test_whitespace_only_instruction(self):
        """Whitespace-only user_instruction → HTTP 422 INVALID_CONTEXT."""
        payload = _make_clean_payload(user_instruction="    ")
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.json()["error"]["code"], "INVALID_CONTEXT")

    def test_missing_user_instruction_field(self):
        """Missing user_instruction field entirely → HTTP 400 INVALID_REQUEST."""
        payload = _make_clean_payload()
        del payload["user_instruction"]
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"]["code"], "INVALID_REQUEST")

    def test_missing_sanitized_dom_field(self):
        """Missing sanitized_dom field → HTTP 400 INVALID_REQUEST."""
        payload = _make_clean_payload()
        del payload["sanitized_dom"]
        res = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"]["code"], "INVALID_REQUEST")

    def test_raw_fields_not_accepted(self):
        """The schema only accepts sanitized_* fields — extra 'screenshot' or 'dom' fields
        are silently ignored (Pydantic by default). The missing sanitized_* fields cause
        INVALID_REQUEST, ensuring raw fields cannot substitute for sanitized ones."""
        payload = {
            "request_id": "req-raw-bypass",
            "user_instruction": "Click submit",
            # Sending raw field names that should never reach the server
            "screenshot": "data:image/png;base64,rawrawraw",
            "dom": "<div>Password: RawPassword!</div>",
        }
        res = self.client.post("/api/v1/analyze", json=payload)
        # Must fail because sanitized_screenshot and sanitized_dom are missing
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"]["code"], "INVALID_REQUEST")


class TestPrivacyStatusEndpoint(unittest.TestCase):
    """GET /api/v1/privacy-status must return correct integration status."""

    def setUp(self):
        self.client = TestClient(app)

    def test_privacy_status_endpoint_accessible(self):
        """Privacy status endpoint should return HTTP 200."""
        res = self.client.get("/api/v1/privacy-status")
        self.assertEqual(res.status_code, 200)

    def test_privacy_status_fields_present(self):
        """Privacy status response must include all integration fields."""
        res = self.client.get("/api/v1/privacy-status")
        data = res.json()
        self.assertIn("privacy_module_available", data)
        self.assertIn("server_pii_guard_active", data)
        self.assertIn("sanitized_field_enforcement", data)
        self.assertIn("accepted_fields", data)
        self.assertIn("rejected_fields", data)
        self.assertIn("integration_note", data)

    def test_privacy_module_not_yet_available(self):
        """Privacy module (privacy/) is not yet implemented — must report False."""
        res = self.client.get("/api/v1/privacy-status")
        data = res.json()
        self.assertFalse(data["privacy_module_available"])

    def test_server_pii_guard_active(self):
        """Server's last-resort PII guard must always be active."""
        res = self.client.get("/api/v1/privacy-status")
        data = res.json()
        self.assertTrue(data["server_pii_guard_active"])

    def test_sanitized_field_enforcement_active(self):
        """Sanitized field enforcement (schema-level) must be active."""
        res = self.client.get("/api/v1/privacy-status")
        data = res.json()
        self.assertTrue(data["sanitized_field_enforcement"])

    def test_accepted_fields_are_sanitized_only(self):
        """Accepted fields must only be sanitized_* variants."""
        res = self.client.get("/api/v1/privacy-status")
        accepted = res.json()["accepted_fields"]
        for f in accepted:
            self.assertTrue(
                f.startswith("sanitized_") or f in ("user_instruction", "visual_elements"),
                f"Unexpected non-sanitized accepted field: {f}"
            )

    def test_rejected_fields_include_raw_variants(self):
        """Rejected fields list must include raw screenshot and dom."""
        res = self.client.get("/api/v1/privacy-status")
        rejected = res.json()["rejected_fields"]
        self.assertIn("screenshot", rejected)
        self.assertIn("dom", rejected)


class TestSanitizedContextInterface(unittest.TestCase):
    """Unit tests for SanitizedContext dataclass and verify_sanitized_context()."""

    def test_sanitized_context_clean_passes(self):
        """Clean SanitizedContext with no raw PII must pass verification."""
        ctx = SanitizedContext(
            request_id="req-001",
            user_instruction="Click the submit button",
            sanitized_screenshot="data:image/png;base64,abc123==",
            sanitized_dom="<button id='btn'>Submit</button>",
            visual_elements=[{"type": "button", "id": "btn"}],
        )
        result = verify_sanitized_context(ctx)
        self.assertIsNone(result)

    def test_sanitized_context_with_raw_password_fails(self):
        """SanitizedContext with unredacted password must fail verification."""
        ctx = SanitizedContext(
            request_id="req-002",
            user_instruction="Login",
            sanitized_screenshot="data:image/png;base64,abc123==",
            sanitized_dom="<div>password: NotRedacted123</div>",
        )
        result = verify_sanitized_context(ctx)
        self.assertIsNotNone(result)
        self.assertIn("raw_password", result)

    def test_sanitized_context_with_raw_email_fails(self):
        """SanitizedContext with unredacted email must fail verification."""
        ctx = SanitizedContext(
            request_id="req-003",
            user_instruction="Send email to user@secret.com",
            sanitized_screenshot="data:image/png;base64,abc123==",
            sanitized_dom="<div>Contact</div>",
        )
        result = verify_sanitized_context(ctx)
        self.assertIsNotNone(result)
        self.assertIn("raw_email", result)

    def test_sanitized_context_with_tokens_passes(self):
        """SanitizedContext with [EMAIL] and [REDACTED] tokens must pass verification."""
        ctx = SanitizedContext(
            request_id="req-004",
            user_instruction="Fill the form",
            sanitized_screenshot="data:image/png;base64,abc123==",
            sanitized_dom=(
                "<form>"
                "<input name='email' value='[EMAIL]' />"
                "<input type='password' value='[REDACTED]' />"
                "<input name='phone' value='[PHONE]' />"
                "</form>"
            ),
        )
        result = verify_sanitized_context(ctx)
        self.assertIsNone(result)

    def test_privacy_module_not_available(self):
        """privacy_module_is_available() must return False (placeholder-only module)."""
        self.assertFalse(privacy_module_is_available())

    def test_integration_status_structure(self):
        """INTEGRATION_STATUS dict must have all required keys."""
        required_keys = [
            "privacy_module_available",
            "server_pii_guard_active",
            "sanitized_field_enforcement",
            "integration_note",
        ]
        for key in required_keys:
            self.assertIn(key, INTEGRATION_STATUS)


class TestCheckSanitizedFieldsUnit(unittest.TestCase):
    """Unit tests for check_sanitized_fields() covering each PII category."""

    def _check(self, dom="", instruction="Click", screenshot="data:image/png;base64,validscreenshot"):
        return check_sanitized_fields(
            sanitized_screenshot=screenshot,
            sanitized_dom=dom,
            user_instruction=instruction,
        )

    def test_clean_fields_return_none(self):
        self.assertIsNone(self._check(dom="<button>OK</button>"))

    def test_detects_raw_password_in_dom(self):
        result = self._check(dom="password: Secret123")
        self.assertIsNotNone(result)
        self.assertIn("raw_password", result)

    def test_detects_raw_email_in_dom(self):
        result = self._check(dom="<p>admin@corp.io</p>")
        self.assertIsNotNone(result)
        self.assertIn("raw_email", result)

    def test_detects_raw_phone_in_dom(self):
        result = self._check(dom="<p>Call: +44 20 7946 0958</p>")
        self.assertIsNotNone(result)
        self.assertIn("raw_phone", result)

    def test_detects_raw_card_in_dom(self):
        result = self._check(dom="<p>Card: 5500 0000 0000 0004</p>")
        self.assertIsNotNone(result)
        self.assertIn("raw_card_number", result)

    def test_masked_password_not_flagged(self):
        self.assertIsNone(self._check(dom="<input value='[REDACTED]' />"))

    def test_masked_email_not_flagged(self):
        self.assertIsNone(self._check(dom="<p>Email: [EMAIL]</p>"))

    def test_masked_phone_not_flagged(self):
        self.assertIsNone(self._check(dom="<p>Phone: [PHONE]</p>"))

    def test_masked_card_not_flagged(self):
        self.assertIsNone(self._check(dom="<p>Card: [CARD]</p>"))

    def test_raw_email_in_instruction_detected(self):
        result = self._check(instruction="Login as alice@example.org")
        self.assertIsNotNone(result)
        self.assertIn("raw_email", result)


if __name__ == "__main__":
    unittest.main()
