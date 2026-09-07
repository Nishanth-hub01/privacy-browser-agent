# Privacy-Preserving Vision Browser Agent

# Test Plan

**Version:** 1.0.0

---

## 1. Purpose

This document defines the testing strategy for the Privacy-Preserving Vision Browser Agent.

The purpose of testing is to verify that:

* Each project module works correctly.
* Modules communicate according to the shared API contract.
* Sensitive information is detected and protected locally.
* Raw private information never reaches the server.
* Sanitized screenshots and DOM data are correctly processed.
* The Server + AI module returns valid browser actions.
* The Browser Extension safely executes valid actions.
* The complete end-to-end system works correctly.
* Performance and privacy requirements can be measured.

---

## 2. System Under Test

The system contains the following major modules:

```text
Browser Extension
        |
        v
Local Privacy + Vision AI
        |
        v
Sanitized Data
        |
        v
FastAPI Server
        |
        v
VLM / LLM Agent
        |
        v
Action JSON
        |
        v
Browser Extension
        |
        v
Browser Action
```

---

## 3. Testing Objectives

The main testing objectives are:

1. Verify browser screenshot capture.
2. Verify DOM extraction.
3. Verify sensitive information detection.
4. Verify screenshot redaction.
5. Verify DOM sanitization.
6. Verify privacy verification before transmission.
7. Verify API request and response formats.
8. Verify AI action generation.
9. Verify action validation.
10. Verify safe browser action execution.
11. Verify error handling.
12. Verify end-to-end functionality.
13. Measure system performance.
14. Ensure raw private data never leaves the browser.

---

## 4. Testing Levels

### 4.1 Unit Testing

Tests individual functions.

Examples:

```text
Screenshot function
DOM extraction function
Email detection function
Password detection function
Redaction function
Action validation function
```

---

### 4.2 Module Testing

Tests each major module independently.

```text
Extension
Privacy
Server
Agent
```

Each team member is responsible for testing their assigned module.

---

### 4.3 Integration Testing

Tests communication between modules.

```text
Extension → Privacy
Privacy → Server
Server → Extension
```

---

### 4.4 End-to-End Testing

Tests the complete workflow:

```text
User Instruction
       ↓
Browser Extension
       ↓
Privacy + Vision AI
       ↓
Sanitized Context
       ↓
FastAPI Server
       ↓
VLM / LLM
       ↓
Action JSON
       ↓
Browser Extension
       ↓
Browser Action
```

---

## 5. Test Modules

| Module      | Main Responsibility                              | Owner       |
| ----------- | ------------------------------------------------ | ----------- |
| Extension   | Screenshot, DOM, communication, action execution | Member 1    |
| Privacy     | PII detection, redaction, DOM sanitization       | Member 2    |
| Server      | API, validation, communication                   | Member 3    |
| Agent       | VLM/LLM reasoning and action planning            | Member 3    |
| Integration | Complete system testing                          | All Members |

---

## 6. Test Environment

Testing may use:

### Browser

```text
Google Chrome
Mozilla Firefox
```

### Extension

```text
Manifest V3
JavaScript / TypeScript
Browser Extension APIs
```

### Privacy

```text
ONNX Runtime Web
WebGPU
WebAssembly
Transformers.js
Computer Vision models
```

### Server

```text
Python
FastAPI
Pydantic
```

### AI

```text
VLM / LLM
Mock model for early testing
```

---

## 7. Test Data

Use **synthetic test data**.

Example:

```text
Name:
Fake Person

Email:
test@example.com

Phone:
9000000000

Password:
FakePassword123
```

Do NOT use:

* Real passwords
* Real credit card numbers
* Real government IDs
* Real personal documents
* Other real sensitive information

---

## 8. Privacy Testing

Privacy is a critical requirement of this project.

### Main Rule

> RAW PRIVATE DATA MUST NEVER BE SENT TO THE SERVER.

Testing must verify:

```text
Raw Screenshot + DOM
        ↓
Local Privacy Detection
        ↓
Redaction
        ↓
Privacy Verification
        ↓
Sanitized Screenshot + DOM
        ↓
Server
```

If raw sensitive information reaches the server, the test must be marked as a **critical failure**.

---

## 9. Sensitive Information Test Categories

The Privacy module should be tested for:

```text
Password
Email
Phone Number
Government ID
Credit/Debit Card
Face
Personal Name
Sensitive Form Fields
```

Example:

### Input

```text
Name: Fake Person
Email: test@example.com
Password: FakePassword123
```

### Expected Output

```text
Name: [PERSON]
Email: [EMAIL]
Password: [REDACTED]
```

---

## 10. API Testing

The API must follow:

```text
shared/API_CONTRACT.md
```

The following must be tested:

* Required fields
* Data types
* Valid requests
* Invalid requests
* Error responses
* Action formats
* Confidence values

Main endpoint:

```text
POST /api/v1/analyze
```

---

## 11. Browser Action Testing

Initially supported actions:

```text
click
scroll
type
navigate
```

Each action must be tested independently.

Example:

```json
{
  "type": "click",
  "target": {
    "id": "upload-btn"
  }
}
```

The Extension should validate the action before executing it.

---

## 12. Confidence Testing

The AI returns a confidence value between:

```text
0.0 and 1.0
```

Initial rule:

```text
confidence >= 0.80
        ↓
Action can be executed

confidence < 0.80
        ↓
Ask user / request clarification
```

Test examples:

```text
0.96 → High confidence
0.85 → Acceptable confidence
0.55 → Low confidence
0.20 → Very low confidence
```

Low-confidence actions must not be silently executed.

---

## 13. Error Testing

The following errors should be tested:

```text
INVALID_REQUEST
INVALID_CONTEXT
PRIVACY_CHECK_FAILED
MODEL_ERROR
ACTION_NOT_FOUND
LOW_CONFIDENCE
SERVER_ERROR
```

The system should fail safely.

Example:

```text
Privacy verification fails
        ↓
Do NOT send data
        ↓
Return safe error
```

---

## 14. Performance Testing

The project should measure:

### Latency

```text
Screenshot capture time
DOM extraction time
Privacy processing time
AI inference time
Server response time
Total end-to-end latency
```

### Resource Usage

```text
CPU usage
GPU usage
Memory usage
Browser extension resource usage
```

### Privacy AI

Measure:

```text
Detection time
Redaction time
Sanitization time
```

---

## 15. Evaluation Metrics

The project should track the following major metrics:

| Metric                      | Target Area              |
| --------------------------- | ------------------------ |
| Visual Context Accuracy     | Browser understanding    |
| PII Detection Precision     | Sensitive data detection |
| PII Detection Recall        | Sensitive data detection |
| Redaction Precision         | Correct redaction        |
| Client Resource Utilization | CPU/GPU/Memory           |
| End-to-End Latency          | Overall system speed     |

These measurements will be used during final evaluation.

---

## 16. Mock Testing

Before connecting a real VLM/LLM, use a mock response.

Example:

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

This allows the team to test the complete system before integrating the real AI model.

---

## 17. Test Ownership

### Member 1

Responsible for:

```text
tests/extension/
```

Tests:

* Screenshot capture
* DOM extraction
* User instruction
* API communication
* Action execution

---

### Member 2

Responsible for:

```text
tests/privacy/
```

Tests:

* PII detection
* Password detection
* Face detection
* Screenshot redaction
* DOM sanitization
* Privacy verification

---

### Member 3

Responsible for:

```text
tests/server/
```

Tests:

* FastAPI endpoint
* Request validation
* AI response
* Action generation
* Confidence
* Error handling

---

### All Members

Responsible for:

```text
tests/integration/
```

Tests:

* Extension → Privacy
* Privacy → Server
* Server → Extension
* Complete end-to-end workflow

---

## 18. Test Result Status

Use the following status:

```text
PASS
FAIL
BLOCKED
NOT TESTED
```

Example:

| Test               | Status     | Notes                    |
| ------------------ | ---------- | ------------------------ |
| Screenshot Capture | PASS       | Working correctly        |
| Email Detection    | PASS       | Detected synthetic email |
| Password Redaction | PASS       | Password removed         |
| API Request        | PASS       | Valid response           |
| Click Action       | NOT TESTED | Waiting for extension    |
| End-to-End         | BLOCKED    | Server not connected     |

---

## 19. Critical Failure Conditions

The following are considered critical failures:

1. Raw PII reaches the server.
2. Raw passwords reach the server.
3. Privacy verification can be bypassed.
4. Invalid AI actions are executed.
5. Malicious or malformed actions are executed.
6. Extension crashes during normal operation.
7. Sensitive screenshot regions remain readable after required redaction.

Critical failures must be fixed before the final demonstration.

---

## 20. Final Acceptance Criteria

The project is ready for final demonstration when:

* [ ] Extension tests pass.
* [ ] Privacy tests pass.
* [ ] Server tests pass.
* [ ] Integration tests pass.
* [ ] End-to-end workflow works.
* [ ] Privacy boundary is verified.
* [ ] PII detection is measured.
* [ ] Redaction quality is measured.
* [ ] Client resource usage is measured.
* [ ] End-to-end latency is measured.
* [ ] Low-confidence actions are handled safely.
* [ ] Invalid actions are rejected.
* [ ] Error handling works.
* [ ] No real sensitive data was used during testing.

---

## 21. Final Test Scenario

The primary demonstration scenario should be:

```text
User:
"Find the upload button"
        ↓
Extension captures page
        ↓
Privacy AI detects sensitive information
        ↓
Sensitive information is redacted
        ↓
Privacy verification
        ↓
Sanitized data sent to server
        ↓
VLM / LLM understands page
        ↓
Returns:
click(upload-btn)
        ↓
Extension validates action
        ↓
Browser clicks Upload button
```

Expected result:

```text
✓ Correct browser understanding
✓ Sensitive data protected
✓ Only sanitized data sent
✓ Correct AI action
✓ Safe action execution
```

---

## 22. Core Testing Principle

The most important rule for the entire project is:

> **Privacy must be verified before any data is sent to the server.**

The system must always follow:

```text
COLLECT
   ↓
DETECT
   ↓
REDACT
   ↓
VERIFY
   ↓
SEND SANITIZED DATA
   ↓
REASON
   ↓
VALIDATE ACTION
   ↓
EXECUTE
```
