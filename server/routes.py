"""API route handlers for POST /api/v1/analyze and GET /api/v1/privacy-status.

Field contract (API_CONTRACT.md §6):
  Accepted fields (sanitized only):
    - sanitized_screenshot   base64-encoded, face/PII-blurred image
    - sanitized_dom          HTML with sensitive values redacted
    - visual_elements        list of safe element descriptors (no raw PII)
    - user_instruction       natural-language instruction

  Rejected fields (must NEVER be sent):
    - screenshot             raw screenshot
    - dom                    raw DOM
    - any raw PII values     passwords, emails, phone numbers, card numbers

Pipeline: Request → Privacy guard → Context validity → Agent → Confidence → Action schema → Response
"""
import logging
import sys
from pathlib import Path

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

# Ensure both server/ and workspace root are in sys.path
SERVER_DIR = Path(__file__).resolve().parent
ROOT_DIR = SERVER_DIR.parent
for p in (str(ROOT_DIR), str(SERVER_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from server.schemas import (
        AnalyzeRequest,
        ServerSuccessResponse,
        ErrorResponse,
        ErrorDetail,
        ErrorCode,
        ServerResponse,
    )
    from server.validator import (
        check_privacy_violations,
        check_context_validity,
        validate_browser_action,
        validate_confidence,
        is_low_confidence,
    )
    from server.privacy_interface import INTEGRATION_STATUS
except ModuleNotFoundError:
    from schemas import (
        AnalyzeRequest,
        ServerSuccessResponse,
        ErrorResponse,
        ErrorDetail,
        ErrorCode,
        ServerResponse,
    )
    from validator import (
        check_privacy_violations,
        check_context_validity,
        validate_browser_action,
        validate_confidence,
        is_low_confidence,
    )
    from privacy_interface import INTEGRATION_STATUS

try:
    from agent import BrowserAgent, AgentContext
    from agent.exceptions import (
        ModelJSONDecodeError,
        UnsupportedActionError,
        InvalidActionTargetError,
        InvalidConfidenceError,
        InvalidReasonError,
    )
except (ModuleNotFoundError, ImportError):
    BrowserAgent = None
    AgentContext = None
    ModelJSONDecodeError = ()
    UnsupportedActionError = ()
    InvalidActionTargetError = ()
    InvalidConfidenceError = ()
    InvalidReasonError = ()

logger = logging.getLogger("server.routes")

# Initialize agent instance with MockPlanner (replaced by LLMPlanner in a later phase)
agent = BrowserAgent() if BrowserAgent else None

router = APIRouter(prefix="/api/v1", tags=["analyze"])


@router.get("/privacy-status", tags=["privacy"])
async def privacy_status():
    """Return the current privacy module integration status.

    Informs the Extension and team whether the Privacy module (privacy/) has been
    connected to the server. When privacy_module_available is False, the Extension
    must manually provide already-sanitized fields in its POST /api/v1/analyze body.
    """
    return {
        "privacy_module_available": INTEGRATION_STATUS["privacy_module_available"],
        "server_pii_guard_active": INTEGRATION_STATUS["server_pii_guard_active"],
        "sanitized_field_enforcement": INTEGRATION_STATUS["sanitized_field_enforcement"],
        "accepted_fields": [
            "sanitized_screenshot",
            "sanitized_dom",
            "visual_elements",
            "user_instruction",
        ],
        "rejected_fields": [
            "screenshot",
            "dom",
            "raw_*",
        ],
        "integration_note": INTEGRATION_STATUS["integration_note"],
    }


def _error(request_id: str, code: ErrorCode, message: str, http_status: int) -> JSONResponse:
    """Build a contract-compliant JSON error response.

    Centralises error construction so all error paths have identical structure.
    """
    logger.warning("[%s] %s: %s", request_id, code.value, message)
    return JSONResponse(
        status_code=http_status,
        content=ErrorResponse(
            request_id=request_id,
            status="error",
            error=ErrorDetail(code=code, message=message),
        ).model_dump(),
    )


@router.post(
    "/analyze",
    response_model=ServerResponse,
    responses={
        200: {"model": ServerResponse, "description": "Successful action or low-confidence notice"},
        400: {"model": ErrorResponse, "description": "Invalid request or privacy violation"},
        422: {"model": ErrorResponse, "description": "Invalid context or action schema failure"},
        500: {"model": ErrorResponse, "description": "Internal model/server error"},
    },
)
async def analyze_webpage(request: AnalyzeRequest):
    """Analyze sanitized browser context and plan the next browser action.

    Pipeline (per API_CONTRACT.md):
      1. PRIVACY_CHECK_FAILED  — raw PII/passwords detected in payload
      2. INVALID_CONTEXT       — sanitized content is empty or unusable
      3. SERVER_ERROR          — agent is unavailable
      4. MODEL_ERROR           — agent raised an exception during planning
      5. ACTION_NOT_FOUND      — agent returned an empty or no action
      6. MODEL_ERROR           — agent returned an out-of-range confidence value
      7. ACTION_NOT_FOUND      — planned action fails schema validation
      8. LOW_CONFIDENCE        — confidence < 0.80; extension must NOT auto-execute
      9. success               — well-formed action with confidence ≥ 0.80
    """
    rid = request.request_id
    logger.info("[%s] Received analyze request: %r", rid, request.user_instruction)

    # ── Step 1: Privacy boundary check (API_CONTRACT.md §3) ──────────────────
    privacy_violation = check_privacy_violations(request)
    if privacy_violation:
        return _error(rid, ErrorCode.PRIVACY_CHECK_FAILED, privacy_violation,
                      status.HTTP_400_BAD_REQUEST)

    # ── Step 2: Context integrity check ──────────────────────────────────────
    context_error = check_context_validity(request)
    if context_error:
        return _error(rid, ErrorCode.INVALID_CONTEXT, context_error,
                      status.HTTP_422_UNPROCESSABLE_ENTITY)

    # ── Step 3: Agent availability ───────────────────────────────────────────
    if not agent:
        return _error(
            rid, ErrorCode.SERVER_ERROR,
            "Agent planning engine is not available. The server may be misconfigured.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # ── Step 4: Build agent context ──────────────────────────────────────────
    try:
        context = AgentContext(
            user_instruction=request.user_instruction,
            sanitized_screenshot=request.sanitized_screenshot,
            sanitized_dom=request.sanitized_dom,
            visual_elements=[el.model_dump() for el in request.visual_elements],
        )
    except Exception as ctx_err:
        return _error(
            rid, ErrorCode.INVALID_CONTEXT,
            f"Failed to build agent context from request data: {ctx_err}",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # ── Step 5: Agent planning ───────────────────────────────────────────────
    try:
        plan_result = await agent.act(context)
    except (UnsupportedActionError, InvalidActionTargetError) as act_err:
        logger.warning("[%s] Action validation failed: %s", rid, act_err)
        return _error(
            rid, ErrorCode.ACTION_NOT_FOUND,
            f"The model planned an invalid or unsupported action: {act_err}",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    except (ModelJSONDecodeError, InvalidConfidenceError, InvalidReasonError) as mod_err:
        logger.warning("[%s] Model output validation failed: %s", rid, mod_err)
        return _error(
            rid, ErrorCode.MODEL_ERROR,
            f"The model output failed validation: {mod_err}",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    except Exception as exc:
        logger.exception("[%s] Agent planning raised an exception", rid)
        return _error(
            rid, ErrorCode.MODEL_ERROR,
            f"Agent planning encountered an internal error: {exc}",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # ── Step 6: Empty result guard ────────────────────────────────────────────
    if not plan_result or not plan_result.action:
        return _error(
            rid, ErrorCode.ACTION_NOT_FOUND,
            "The agent could not determine a valid browser action for the given instruction.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # ── Step 7: Confidence range validation ──────────────────────────────────
    try:
        safe_confidence = validate_confidence(plan_result.confidence)
    except (TypeError, ValueError) as conf_err:
        return _error(
            rid, ErrorCode.MODEL_ERROR,
            f"Agent returned an invalid confidence value: {conf_err}",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # ── Step 8: Action schema validation ─────────────────────────────────────
    try:
        validated_action = validate_browser_action(plan_result.action)
    except Exception as val_err:
        return _error(
            rid, ErrorCode.ACTION_NOT_FOUND,
            f"Agent returned an action that failed schema validation: {val_err}",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # ── Step 9: Confidence threshold (API_CONTRACT.md §9) ────────────────────
    # confidence >= 0.80 → return action for execution
    # confidence <  0.80 → LOW_CONFIDENCE; extension must NOT auto-execute
    if is_low_confidence(safe_confidence):
        return _error(
            rid, ErrorCode.LOW_CONFIDENCE,
            (
                f"Action confidence ({safe_confidence:.2f}) is below the 0.80 threshold. "
                "Please clarify the instruction or confirm the intended action."
            ),
            status.HTTP_200_OK,
        )

    # ── Step 10: Success response ─────────────────────────────────────────────
    logger.info(
        "[%s] Action planned: type=%r confidence=%.2f reason=%r",
        rid, validated_action.type, safe_confidence, plan_result.reason,
    )
    return ServerSuccessResponse(
        request_id=rid,
        status="success",
        action=validated_action,
        confidence=safe_confidence,
        reason=plan_result.reason,
    )
