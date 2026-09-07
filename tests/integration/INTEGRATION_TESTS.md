# Integration and End-to-End Tests

**Version:** 1.0.0
**Owners:** All Team Members

---

## 1. Purpose

This document defines the integration and end-to-end tests for the Privacy-Preserving Vision Browser Agent.

The purpose is to verify that all major modules work together correctly.

The complete system is:

```text
User
  ↓
Browser Extension
  ↓
Local Privacy + Vision AI
  ↓
Sanitized Data
  ↓
FastAPI Server
  ↓
VLM / LLM Agent
  ↓
Action JSON
  ↓
Browser Extension
  ↓
Browser Action
```

---

# 2. Integration Components

The following components are tested together:

```text
extension/
privacy/
server/
agent/
shared/
```

The integration tests must follow:

```text
shared/API_CONTRACT.md
```

and the shared TypeScript definitions in:

```text
shared/types.ts
```

---

# 3. Integration Test Levels

Integration testing is divided into:

### Level 1

```text
Extension → Privacy
```

### Level 2

```text
Privacy → Server
```

### Level 3

```text
Server → Extension
```

### Level 4

```text
Complete End-to-End
```

---

# 4. Extension → Privacy Test

## INT-001

**Test:** Send webpage context from Extension to Privacy module.

### Input

```text
User instruction:
Find the upload button
```

The Extension should provide:

```text
Screenshot
DOM
URL
User instruction
Request ID
Timestamp
```

### Expected Result

```text
Extension
    ↓
Privacy Module
```

Privacy module successfully receives the request.

**Status:**

```text
NOT TESTED
```

---

# 5. Privacy Processing Test

## INT-002

**Test:** Privacy module processes webpage context.

### Input

Synthetic webpage data:

```text
Name: Fake Person
Email: test@example.com
Password: FakePassword123
```

### Expected Result

Sensitive information is detected and sanitized.

```text
Name: [PERSON]
Email: [EMAIL]
Password: [REDACTED]
```

**Status:**

```text
NOT TESTED
```

---

# 6. Privacy → Server Test

## INT-003

**Test:** Send sanitized context to Server.

### Expected Data

```text
sanitized_screenshot
sanitized_dom
visual_elements
user_instruction
request_id
```

### Expected Flow

```text
Privacy Module
      ↓
Privacy Verification
      ↓
Sanitized Data
      ↓
FastAPI Server
```

### Critical Requirement

Raw sensitive information must NOT be included.

**Status:**

```text
NOT TESTED
```

---

# 7. Privacy Boundary Test

## INT-004

**Test:** Verify raw private information cannot bypass the Privacy module.

### Incorrect Flow

```text
Extension
    ↓
Raw Screenshot + DOM
    ↓
Server
```

### Correct Flow

```text
Extension
    ↓
Privacy
    ↓
Redaction
    ↓
Verification
    ↓
Sanitized Data
    ↓
Server
```

### Expected Result

The Server receives only sanitized information.

If raw PII reaches the Server:

```text
TEST = FAIL
SEVERITY = CRITICAL
```

**Status:**

```text
NOT TESTED
```

---

# 8. Server API Test

## INT-005

**Test:** Server receives valid sanitized request.

### Endpoint

```text
POST /api/v1/analyze
```

### Expected Result

```text
HTTP request succeeds
Request is validated
AI processing starts
```

**Status:**

```text
NOT TESTED
```

---

# 9. Server → Agent Test

## INT-006

**Test:** Server passes sanitized context to the VLM/LLM Agent.

### Input

```text
User instruction:
Find the upload button
```

### Expected Result

Agent receives:

```text
User instruction
Sanitized screenshot
Sanitized DOM
Visual elements
```

The Agent must not require raw private information.

**Status:**

```text
NOT TESTED
```

---

# 10. Agent Action Generation Test

## INT-007

**Test:** Agent generates a valid browser action.

### Expected Response

```json
{
  "request_id": "req-001",
  "status": "success",
  "action": {
    "type": "click",
    "target": {
      "id": "upload-btn"
    }
  },
  "confidence": 0.96,
  "reason": "The Upload Document button matches the user's instruction."
}
```

### Expected Result

Server returns valid action JSON.

**Status:**

```text
NOT TESTED
```

---

# 11. Server → Extension Test

## INT-008

**Test:** Extension receives AI action from Server.

### Expected Flow

```text
Server
   ↓
Action JSON
   ↓
Extension
```

### Expected Result

Extension:

```text
Receives response
      ↓
Validates response
      ↓
Validates action
      ↓
Checks confidence
```

**Status:**

```text
NOT TESTED
```

---

# 12. Click Action End-to-End Test

## INT-009

### User Instruction

```text
Find the upload button
```

### Expected Flow

```text
User
 ↓
Extension
 ↓
Screenshot + DOM
 ↓
Privacy
 ↓
PII Detection
 ↓
Redaction
 ↓
Privacy Verification
 ↓
Sanitized Data
 ↓
Server
 ↓
VLM / LLM
 ↓
click(upload-btn)
 ↓
Extension
 ↓
Action Validation
 ↓
Browser
 ↓
Upload Button Clicked
```

### Expected Result

```text
Upload button is clicked successfully.
```

**Status:**

```text
NOT TESTED
```

---

# 13. Scroll Action End-to-End Test

## INT-010

### User Instruction

```text
Scroll down to find the next section
```

### Expected AI Action

```json
{
  "type": "scroll",
  "target": {
    "direction": "down",
    "amount": 600
  }
}
```

### Expected Result

Browser scrolls downward.

**Status:**

```text
NOT TESTED
```

---

# 14. Type Action End-to-End Test

## INT-011

### User Instruction

```text
Enter the test email in the email field
```

### Expected AI Action

```json
{
  "type": "type",
  "target": {
    "id": "email-input"
  },
  "text": "test@example.com"
}
```

### Expected Result

The test email is entered into the correct field.

Use only synthetic test data.

**Status:**

```text
NOT TESTED
```

---

# 15. Navigate Action End-to-End Test

## INT-012

### User Instruction

```text
Open the documentation page
```

### Expected AI Action

```json
{
  "type": "navigate",
  "target": {
    "url": "https://example.com/docs"
  }
}
```

### Expected Result

Browser navigates to the validated URL.

**Status:**

```text
NOT TESTED
```

---

# 16. Low Confidence Test

## INT-013

**Test:** AI returns low confidence.

### Example

```text
confidence = 0.55
```

### Expected Flow

```text
AI
 ↓
confidence < 0.80
 ↓
Extension rejects automatic execution
 ↓
User clarification / approval
```

### Expected Result

The action must NOT be silently executed.

**Status:**

```text
NOT TESTED
```

---

# 17. Invalid Action Test

## INT-014

**Test:** Server returns unsupported action.

### Example

```json
{
  "type": "delete_everything"
}
```

### Expected Result

```text
Extension
    ↓
Action validation
    ↓
Action rejected
```

No browser action should be executed.

**Status:**

```text
NOT TESTED
```

---

# 18. Privacy Failure Test

## INT-015

**Test:** Privacy verification fails.

### Expected Flow

```text
Privacy Detection
       ↓
Verification
       ↓
FAIL
       ↓
Block Server Request
```

### Expected Result

No data is sent to the Server.

**Status:**

```text
NOT TESTED
```

---

# 19. Server Failure Test

## INT-016

**Test:** Server becomes unavailable.

### Expected Result

```text
Extension
    ↓
Request timeout/error
    ↓
Safe error handling
```

The browser should remain stable.

Raw private data must not be sent through another unsafe path.

**Status:**

```text
NOT TESTED
```

---

# 20. AI Failure Test

## INT-017

**Test:** VLM/LLM fails to generate an action.

### Expected Result

Server returns:

```text
MODEL_ERROR
```

Extension handles the error safely.

No invalid action is executed.

**Status:**

```text
NOT TESTED
```

---

# 21. Request ID Test

## INT-018

**Test:** Verify the same request ID is maintained through the system.

### Example

```text
Extension:
req-001

Privacy:
req-001

Server:
req-001

Response:
req-001
```

### Expected Result

The request can be traced across modules using the same `request_id`.

**Status:**

```text
NOT TESTED
```

---

# 22. Mock Integration Test

Before connecting the real VLM/LLM, use a mock AI response.

### Input

```text
Find the upload button
```

### Mock Response

```json
{
  "request_id": "req-001",
  "status": "success",
  "action": {
    "type": "click",
    "target": {
      "id": "upload-btn"
    }
  },
  "confidence": 0.96,
  "reason": "The Upload Document button matches the user's instruction."
}
```

### Expected Result

The Extension receives the mock response and clicks the correct button.

This allows integration testing before the real AI model is connected.

**Status:**

```text
NOT TESTED
```

---

# 23. Complete End-to-End Test

## INT-019

This is the most important integration test.

### Scenario

A webpage contains:

```text
Name: Fake Person
Email: test@example.com
Password: FakePassword123

[Upload Document]
[Submit]
```

The user says:

```text
Find the upload button
```

### Expected System Behavior

```text
1. Extension captures screenshot.
          ↓
2. Extension extracts DOM.
          ↓
3. Privacy detects sensitive information.
          ↓
4. Privacy redacts sensitive information.
          ↓
5. Privacy verifies sanitized context.
          ↓
6. Sanitized context goes to Server.
          ↓
7. VLM/LLM identifies Upload Document.
          ↓
8. Server returns click action.
          ↓
9. Extension validates action.
          ↓
10. Extension clicks Upload Document.
```

### Expected Final Result

```text
✓ Correct button identified
✓ Sensitive data protected
✓ Only sanitized data sent
✓ Valid action returned
✓ Action validated
✓ Browser action executed
```

**Status:**

```text
NOT TESTED
```

---

# 24. Integration Test Checklist

Before integration is considered complete:

* [ ] Extension → Privacy works.
* [ ] Privacy → Server works.
* [ ] Server → Extension works.
* [ ] Screenshot flow works.
* [ ] DOM flow works.
* [ ] PII detection works.
* [ ] Screenshot redaction works.
* [ ] DOM sanitization works.
* [ ] Privacy verification works.
* [ ] Server API works.
* [ ] Agent returns valid JSON.
* [ ] Action validation works.
* [ ] Click action works.
* [ ] Scroll action works.
* [ ] Type action works.
* [ ] Navigate action works.
* [ ] Low-confidence actions are blocked.
* [ ] Invalid actions are rejected.
* [ ] Privacy failures block transmission.
* [ ] Server failures are handled.
* [ ] AI failures are handled.
* [ ] Request IDs remain consistent.
* [ ] Complete end-to-end scenario passes.

---

# 25. Final Acceptance Criteria

The integration is considered successful when:

```text
✓ All major modules communicate correctly
✓ API contract is followed
✓ Raw private data never reaches the Server
✓ Sanitized context reaches the AI
✓ AI returns valid actions
✓ Extension validates actions
✓ Browser executes safe actions
✓ Errors are handled safely
✓ Low-confidence actions are not automatically executed
✓ Complete end-to-end test passes
```

---

# 26. Critical Security Rule

The following flow is NEVER allowed:

```text
Raw Webpage Data
       ↓
Server
```

The only allowed flow is:

```text
Raw Webpage Data
       ↓
Local Privacy AI
       ↓
Detection
       ↓
Redaction
       ↓
Verification
       ↓
Sanitized Data
       ↓
Server
```

> **If privacy verification fails, transmission must stop.**
