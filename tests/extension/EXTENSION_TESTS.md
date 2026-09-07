# Browser Extension Tests

**Version:** 1.0.0
**Owner:** Member 1 - Browser Extension

---

## 1. Purpose

This document defines the tests for the Browser Extension module.

The Extension is responsible for:

* Capturing screenshots
* Extracting DOM
* Receiving user instructions
* Communicating with the local Privacy module
* Sending sanitized data to the Server
* Receiving AI actions
* Validating actions
* Executing safe browser actions

---

## 2. Extension Test Flow

```text
User Instruction
       |
       v
Browser Extension
       |
       ├── Screenshot
       |
       ├── DOM
       |
       └── User Instruction
              |
              v
        Privacy Module
              |
              v
       Sanitized Context
              |
              v
           Server
              |
              v
         Action JSON
              |
              v
        Extension
              |
              v
       Browser Action
```

---

# 3. Screenshot Capture Tests

### EXT-SCREENSHOT-001

**Test:** Capture screenshot of the current webpage.

**Input:**

```text
Open a normal webpage.
```

**Expected Result:**

```text
Screenshot is successfully captured.
```

**Status:**

```text
NOT TESTED
```

---

### EXT-SCREENSHOT-002

**Test:** Verify screenshot is not empty.

**Expected Result:**

```text
Screenshot contains valid image data.
```

**Status:**

```text
NOT TESTED
```

---

### EXT-SCREENSHOT-003

**Test:** Verify screenshot represents the current page.

**Expected Result:**

```text
Captured screenshot matches the currently visible webpage.
```

**Status:**

```text
NOT TESTED
```

---

# 4. DOM Extraction Tests

### EXT-DOM-001

**Test:** Extract DOM from webpage.

**Expected Result:**

```text
DOM is successfully extracted.
```

**Status:**

```text
NOT TESTED
```

---

### EXT-DOM-002

**Test:** Verify important interactive elements exist in extracted DOM.

Example:

```html
<button id="upload-btn">
    Upload Document
</button>
```

**Expected Result:**

The button should be available in the extracted DOM.

**Status:**

```text
NOT TESTED
```

---

### EXT-DOM-003

**Test:** Handle complex webpage DOM.

**Expected Result:**

```text
Extension does not crash.
DOM extraction completes successfully.
```

**Status:**

```text
NOT TESTED
```

---

# 5. User Instruction Tests

### EXT-INSTRUCTION-001

**Test:** Receive a valid user instruction.

**Input:**

```text
Find the upload button
```

**Expected Result:**

```text
Instruction is accepted.
```

**Status:**

```text
NOT TESTED
```

---

### EXT-INSTRUCTION-002

**Test:** Handle empty instruction.

**Input:**

```text
""
```

**Expected Result:**

```text
Extension rejects the request or asks the user for an instruction.
```

**Status:**

```text
NOT TESTED
```

---

# 6. Extension -> Privacy Tests

### EXT-PRIVACY-001

**Test:** Send screenshot, DOM, URL and user instruction to the local Privacy module.

**Expected Request:**

```json
{
  "request_id": "req-001",
  "timestamp": "2026-09-07T10:30:00Z",
  "url": "https://example.com",
  "screenshot": "<BASE64_IMAGE>",
  "dom": "<HTML_CONTENT>",
  "user_instruction": "Find the upload button"
}
```

**Expected Result:**

Privacy module receives the request successfully.

**Status:**

```text
NOT TESTED
```

---

### EXT-PRIVACY-002

**Test:** Verify request follows `shared/types.ts`.

**Expected Result:**

```text
Request format matches ExtensionPrivacyRequest.
```

**Status:**

```text
NOT TESTED
```

---

# 7. Privacy Boundary Tests

### EXT-PRIVACY-003

**Test:** Ensure raw private data is not sent directly to the Server.

**Expected Flow:**

```text
Extension
    ↓
Privacy Module
    ↓
Sanitized Data
    ↓
Server
```

**Incorrect Flow:**

```text
Extension
    ↓
Raw Data
    ↓
Server
```

**Expected Result:**

```text
Extension never sends raw private context directly to Server.
```

**Status:**

```text
NOT TESTED
```

---

# 8. Sanitized Data Tests

### EXT-SANITIZED-001

**Test:** Receive sanitized data from Privacy module.

**Expected Data:**

```text
sanitized_screenshot
sanitized_dom
visual_elements
```

**Expected Result:**

Extension receives the sanitized response successfully.

**Status:**

```text
NOT TESTED
```

---

# 9. Server Communication Tests

### EXT-SERVER-001

**Test:** Send sanitized context to Server.

**Endpoint:**

```text
POST /api/v1/analyze
```

**Expected Result:**

```text
Server receives valid AnalyzeRequest.
```

**Status:**

```text
NOT TESTED
```

---

### EXT-SERVER-002

**Test:** Handle successful Server response.

Example:

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

**Expected Result:**

Extension receives and parses the response.

**Status:**

```text
NOT TESTED
```

---

### EXT-SERVER-003

**Test:** Handle Server error.

Example:

```json
{
  "request_id": "req-001",
  "status": "error",
  "error": {
    "code": "SERVER_ERROR",
    "message": "Server unavailable."
  }
}
```

**Expected Result:**

```text
Extension handles error safely.
Browser does not crash.
```

**Status:**

```text
NOT TESTED
```

---

# 10. Action Validation Tests

The Extension must validate every action before execution.

Supported actions:

```text
click
scroll
type
navigate
```

---

### EXT-ACTION-001

**Test:** Validate click action.

```json
{
  "type": "click",
  "target": {
    "id": "upload-btn"
  }
}
```

**Expected Result:**

```text
Action is accepted.
```

**Status:**

```text
NOT TESTED
```

---

### EXT-ACTION-002

**Test:** Validate scroll action.

```json
{
  "type": "scroll",
  "target": {
    "direction": "down",
    "amount": 600
  }
}
```

**Expected Result:**

```text
Action is accepted.
```

**Status:**

```text
NOT TESTED
```

---

### EXT-ACTION-003

**Test:** Validate type action.

```json
{
  "type": "type",
  "target": {
    "id": "email-input"
  },
  "text": "test@example.com"
}
```

**Expected Result:**

```text
Action is accepted.
```

Use only synthetic test data.

**Status:**

```text
NOT TESTED
```

---

### EXT-ACTION-004

**Test:** Validate navigate action.

```json
{
  "type": "navigate",
  "target": {
    "url": "https://example.com"
  }
}
```

**Expected Result:**

```text
Action is accepted after URL validation.
```

**Status:**

```text
NOT TESTED
```

---

# 11. Invalid Action Tests

### EXT-ACTION-005

**Test:** Unknown action type.

Example:

```json
{
  "type": "delete_everything"
}
```

**Expected Result:**

```text
Action is rejected.
```

**Status:**

```text
NOT TESTED
```

---

### EXT-ACTION-006

**Test:** Missing target.

Example:

```json
{
  "type": "click"
}
```

**Expected Result:**

```text
Action is rejected.
```

**Status:**

```text
NOT TESTED
```

---

### EXT-ACTION-007

**Test:** Malformed action JSON.

**Expected Result:**

```text
Action is rejected.
No browser action is executed.
```

**Status:**

```text
NOT TESTED
```

---

# 12. Confidence Tests

### EXT-CONFIDENCE-001

**Test:** High-confidence action.

```text
confidence = 0.96
```

**Expected Result:**

```text
Action can be executed.
```

**Status:**

```text
NOT TESTED
```

---

### EXT-CONFIDENCE-002

**Test:** Low-confidence action.

```text
confidence = 0.55
```

**Expected Result:**

```text
Action is not automatically executed.
User clarification or approval is requested.
```

**Status:**

```text
NOT TESTED
```

---

# 13. Browser Action Execution Tests

### EXT-EXEC-001

**Test:** Execute click.

**Input:**

```text
click(upload-btn)
```

**Expected Result:**

```text
Upload button is clicked.
```

**Status:**

```text
NOT TESTED
```

---

### EXT-EXEC-002

**Test:** Execute scroll.

**Input:**

```text
scroll down 600
```

**Expected Result:**

```text
Page scrolls downward.
```

**Status:**

```text
NOT TESTED
```

---

### EXT-EXEC-003

**Test:** Execute type.

**Input:**

```text
type test@example.com into email field
```

**Expected Result:**

```text
Test email is entered into the correct field.
```

**Status:**

```text
NOT TESTED
```

---

### EXT-EXEC-004

**Test:** Execute navigation.

**Input:**

```text
navigate to https://example.com
```

**Expected Result:**

```text
Browser navigates to the validated URL.
```

**Status:**

```text
NOT TESTED
```

---

# 14. Error Handling Tests

Test the Extension when:

* [ ] Privacy module is unavailable.
* [ ] Server is unavailable.
* [ ] Request times out.
* [ ] Invalid response is received.
* [ ] Model returns invalid action.
* [ ] Low-confidence action is received.
* [ ] Target element does not exist.

Expected behavior:

```text
Error
  ↓
Handle safely
  ↓
Do not execute unsafe action
  ↓
Inform user
```

---

# 15. End-to-End Extension Test

## Test: Find Upload Button

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
Capture Screenshot
 ↓
Extract DOM
 ↓
Privacy Module
 ↓
Sanitized Context
 ↓
Server
 ↓
VLM / LLM
 ↓
click(upload-btn)
 ↓
Extension validates action
 ↓
Browser clicks Upload button
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

# 16. Extension Test Checklist

Before considering the Extension module complete:

* [ ] Screenshot capture works.
* [ ] DOM extraction works.
* [ ] User instruction works.
* [ ] Extension → Privacy communication works.
* [ ] Privacy → Extension response works.
* [ ] Only sanitized data is sent to Server.
* [ ] Server communication works.
* [ ] Server errors are handled.
* [ ] Actions are validated.
* [ ] Invalid actions are rejected.
* [ ] Confidence is checked.
* [ ] Click works.
* [ ] Scroll works.
* [ ] Type works.
* [ ] Navigate works.
* [ ] Low-confidence actions are handled safely.
* [ ] End-to-end test passes.

---

# 17. Final Acceptance Criteria

The Extension module is considered ready when:

```text
✓ Screenshot capture works
✓ DOM extraction works
✓ Privacy communication works
✓ Sanitized data reaches Server
✓ AI response is received
✓ Actions are validated
✓ Safe actions are executed
✓ Invalid actions are rejected
✓ Low-confidence actions are handled
✓ Error handling works
✓ End-to-end workflow works
```

The Extension must never bypass the local Privacy module when sending webpage context to the Server.
