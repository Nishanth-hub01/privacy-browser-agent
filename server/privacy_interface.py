"""Privacy Module Integration Interface.

This module defines the minimum interface that connects the server to the
Privacy module (privacy/) once it is ready.

Per API_CONTRACT.md §3 and §6:
  - Raw private data MUST NEVER be sent to the server.
  - Only sanitized data may enter the AI pipeline.
  - The Privacy module is responsible for all detection and redaction.
  - The Server acts as the final safety gate, not the primary privacy layer.

Current status: Privacy module is a placeholder (privacy/ is not yet implemented).
This interface file documents the expected contract so that when the Privacy module
is ready, integration requires only:
  1. Call `verify_sanitized_context()` on the output from the privacy module.
  2. Pass the verified `SanitizedContext` fields to `AnalyzeRequest`.

Nothing in this file depends on the privacy/ module directly. It will remain
safe and importable even when privacy/ does not exist.

DO NOT MODIFY extension/, privacy/, or shared/API_CONTRACT.md.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("server.privacy_interface")

# ─── Sanitized context dataclass ─────────────────────────────────────────────
# This is the shape that the Privacy module must produce.
# The Extension sends raw data → Privacy module sanitizes → produces SanitizedContext
# → Extension POSTs SanitizedContext fields to POST /api/v1/analyze.


@dataclass
class SanitizedContext:
    """Represents the sanitized output produced by the Privacy module.

    All fields here have already had PII, passwords, faces, and other sensitive
    information removed or replaced with safe placeholder tokens such as:
      - [REDACTED]  — passwords
      - [EMAIL]     — email addresses
      - [PHONE]     — phone numbers
      - [PERSON]    — personal names
      - [ID]        — government / national IDs
      - [CARD]      — credit/debit card numbers

    The Privacy module (privacy/) is responsible for producing these values.
    The server only performs a final safety gate check.

    Fields (per API_CONTRACT.md §6 Privacy→Server payload):
        request_id          — same ID as the Extension's original request
        user_instruction    — user's natural-language instruction (from Extension)
        sanitized_screenshot — base64-encoded, face/PII-blurred image
        sanitized_dom       — HTML with sensitive attribute values redacted
        visual_elements     — list of safe element descriptors (no raw PII values)
    """

    request_id: str
    user_instruction: str
    sanitized_screenshot: str
    sanitized_dom: str
    visual_elements: List[Dict[str, Any]] = field(default_factory=list)


# ─── PII detection patterns used as last-resort server guard ─────────────────
# The Privacy module is the primary layer. These patterns provide a secondary
# safety net in case a sanitization step was missed.
#
# Each tuple is (field_name_for_logging, compiled_regex, redaction_token).

_RAW_PII_PATTERNS: List[tuple[str, re.Pattern, str]] = [
    # Unredacted passwords: "password: abc123" but NOT "password: [REDACTED]"
    (
        "raw_password",
        re.compile(
            r"(?i)\bpassword\s*[:=]\s*(?!\[REDACTED\]|\[PASSWORD\]|\*{3,})([^\s\"'<>,;]+)"
        ),
        "[REDACTED]",
    ),
    # Credit/debit card-like 16-digit sequences — checked BEFORE phone to avoid
    # the phone pattern greedily matching card numbers (both are digit sequences).
    (
        "raw_card_number",
        re.compile(
            r"(?<!\[CARD\])"
            r"\b(?:\d{4}[- ]?){3}\d{4}\b"
            r"(?!\])"
        ),
        "[CARD]",
    ),
    # Bare email addresses that were not replaced by [EMAIL]
    (
        "raw_email",
        re.compile(
            r"(?<!\[EMAIL\])"          # not already masked
            r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
            r"(?!\])"                  # not inside a bracket token
        ),
        "[EMAIL]",
    ),
    # Bare phone numbers — require a leading + or area-code parenthesis to avoid
    # matching arbitrary long digit strings (e.g. base64, card numbers already
    # handled above).
    (
        "raw_phone",
        re.compile(
            r"(?<!\[PHONE\])"
            r"(?:\+\d[\d\s\-().]{7,}\d"      # +intl format: +1 800 555 0100
            r"|\(\d{2,4}\)[\d\s\-]{6,}\d"   # (area) format: (020) 7946 0958
            r")"
            r"(?!\d|\])"
        ),
        "[PHONE]",
    ),
]


def check_sanitized_fields(
    sanitized_screenshot: str,
    sanitized_dom: str,
    user_instruction: str,
) -> Optional[str]:
    """Server-side last-resort PII guard (per API_CONTRACT.md §3).

    Scans the incoming sanitized fields for common patterns that should have been
    removed by the Privacy module. Returns an error description string if raw
    sensitive data is detected, or None if the fields appear safe.

    This function is NOT a replacement for the Privacy module — it is a minimal
    safety gate that the server applies after receiving data from the Extension.

    Args:
        sanitized_screenshot: base64-encoded screenshot string.
        sanitized_dom:        sanitized HTML/DOM text.
        user_instruction:     user's natural-language instruction.

    Returns:
        str describing the violation, or None if all fields appear clean.
    """
    fields_to_check = {
        "sanitized_dom": sanitized_dom,
        "user_instruction": user_instruction,
        # Note: sanitized_screenshot is base64 — PII patterns won't match meaningfully.
        # It is checked only for presence/length in check_context_validity().
    }

    for field_name, text in fields_to_check.items():
        if not text:
            continue
        for pii_label, pattern, _token in _RAW_PII_PATTERNS:
            if pattern.search(text):
                logger.warning(
                    "Server privacy guard: %s detected in %s — "
                    "Privacy module may not have fully sanitized this field.",
                    pii_label, field_name,
                )
                return (
                    f"Potentially unsanitized data detected in {field_name} "
                    f"({pii_label}). "
                    "The Privacy module must redact all sensitive data before "
                    "sending to the server."
                )

    return None


# ─── Integration stub ────────────────────────────────────────────────────────

def verify_sanitized_context(ctx: SanitizedContext) -> Optional[str]:
    """Verify a SanitizedContext object produced by the Privacy module.

    This is the entry point that the Extension or a future integration layer
    should call before POSTing to /api/v1/analyze.

    When the Privacy module is fully implemented, the call chain will be:
        Extension (raw data)
            → privacy.sanitize()           [Privacy module's responsibility]
            → SanitizedContext(...)        [privacy/ produces this]
            → verify_sanitized_context()   [server's last-resort check — here]
            → POST /api/v1/analyze

    Currently the Privacy module is not yet implemented, so the Extension must
    manually provide already-sanitized fields in the POST body.

    Returns:
        str with violation description if unsafe data is detected, or None if clean.
    """
    return check_sanitized_fields(
        sanitized_screenshot=ctx.sanitized_screenshot,
        sanitized_dom=ctx.sanitized_dom,
        user_instruction=ctx.user_instruction,
    )


# ─── Integration readiness check ─────────────────────────────────────────────

def privacy_module_is_available() -> bool:
    """Returns True when the Privacy module (privacy/) is fully implemented.

    Checks for the presence of an __init__.py in the workspace's privacy/ directory.
    Currently returns False because privacy/ contains only placeholder files.
    """
    # Resolve the workspace root relative to this file (server/privacy_interface.py)
    workspace_root = Path(__file__).resolve().parent.parent
    privacy_init = workspace_root / "privacy" / "__init__.py"
    return privacy_init.exists()


INTEGRATION_STATUS = {
    "privacy_module_available": privacy_module_is_available(),
    "server_pii_guard_active": True,
    "sanitized_field_enforcement": True,
    "integration_note": (
        "Privacy module (privacy/) is not yet implemented. "
        "The server enforces sanitized field names and applies a secondary PII guard. "
        "When privacy/ is ready, call verify_sanitized_context() before POSTing to /api/v1/analyze."
    ),
}
