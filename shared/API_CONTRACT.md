# Privacy-Preserving Vision Browser Agent
## API Contract

**Version:** 1.0.0

This file defines how our 3 project modules communicate.

---

## 1. System Flow

```text
Browser Extension
       |
       | Screenshot + DOM
       v
Local Privacy + Vision AI
       |
       | Sanitized Data ONLY
       v
FastAPI Server
       |
       v
VLM / LLM
       |
       | Action JSON
       v
Browser Extension
       |
       v
Browser Action
```

---

## 2. Team Responsibilities

### Member 1 - Browser Extension

Folder:
```text
extension/
```

Responsible for:
- Browser extension
- Screenshot capture
- DOM extraction
- User instruction
- Sending data to Privacy module
- Sending sanitized data to Server
- Receiving actions
- Executing browser actions

### Member 2 - Local Privacy + Vision AI

Folder:
```text
privacy/
```

Responsible for:
- Detecting sensitive information
- Detecting PII
- Detecting passwords
- Detecting faces
- Redacting screenshots
- Sanitizing DOM
- Privacy verification
- Local AI inference

### Member 3 - Server + AI

Folders:
```text
server/
agent/
```

Responsible for:
- FastAPI backend
- API endpoints
- VLM/LLM
- AI reasoning
- Action planning
- Returning action JSON

---

# 3. MOST IMPORTANT PRIVACY RULE

## RAW PRIVATE DATA MUST NEVER BE SENT TO THE SERVER.

Correct flow:
```text
Raw Screenshot + DOM
        |
        v
Local Privacy Detection
        |
        v
Redaction
        |
        v
Privacy Verification
        |
        v
Sanitized Screenshot + DOM
        |
        v
Server
```

---

# 4. Sensitive Information

The Privacy module should detect:
- Passwords
- Email addresses
- Phone numbers
- Government IDs
- Credit/debit card numbers
- Faces
- Personal names
- Sensitive form fields

Example:
```text
Before:

Name: John Smith
Email: john@example.com
Password: MyPassword123

After:

Name: [PERSON]
Email: [EMAIL]
Password: [REDACTED]
```

---

# 5. Extension -> Privacy

The Extension sends:
```json
{
  "request_id": "req-001",
  "timestamp": "2026-09-07T10:30:00Z",
  "url": "https://example.com",
  "screenshot": "<BASE64_IMAGE>",
  "dom": "<HTML_CONTENT>",
  "user_instruction": "Find the submit button"
}
```

Required fields:
```text
request_id
timestamp
url
screenshot
dom
user_instruction
```

---

# 6. Privacy -> Server

Only sanitized information can be sent.

Endpoint:
```text
POST /api/v1/analyze
```

Example:
```json
{
  "request_id": "req-001",
  "user_instruction": "Find the submit button",
  "sanitized_screenshot": "<BASE64_SANITIZED_IMAGE>",
  "sanitized_dom": "<SANITIZED_HTML>",
  "visual_elements": [
    {
      "type": "button",
      "label": "Submit",
      "id": "submit-btn"
    }
  ]
}
```

---

# 7. Server -> Extension

The server returns an action.

Example:
```json
{
  "request_id": "req-001",
  "status": "success",
  "action": {
    "type": "click",
    "target": {
      "id": "submit-btn"
    }
  },
  "confidence": 0.96,
  "reason": "The Submit button matches the user's instruction."
}
```

---

# 8. Supported Actions

Initially we support:
```text
click
scroll
type
navigate
```

Example click:
```json
{
  "type": "click",
  "target": {
    "id": "submit-btn"
  }
}
```

Example scroll:
```json
{
  "type": "scroll",
  "target": {
    "direction": "down",
    "amount": 600
  }
}
```

---

# 9. Confidence

The AI must return confidence between:
```text
0.0 and 1.0
```

Initial rule:
```text
confidence >= 0.80
        |
        v
Execute action

confidence < 0.80
        |
        v
Ask user / request clarification
```

---

# 10. Error Response

If something fails:
```json
{
  "request_id": "req-001",
  "status": "error",
  "error": {
    "code": "INVALID_CONTEXT",
    "message": "Sanitized context could not be processed."
  }
}
```

Possible error codes:
```text
INVALID_REQUEST
INVALID_CONTEXT
PRIVACY_CHECK_FAILED
MODEL_ERROR
ACTION_NOT_FOUND
LOW_CONFIDENCE
SERVER_ERROR
```

---

# 11. Integration Order

Build and test in this order:

### Step 1
```text
Extension -> Privacy
```

### Step 2
```text
Privacy -> Server
```

### Step 3
```text
Server -> Extension
```

### Step 4
```text
Complete End-to-End Test
```

---

# 12. Git Rules

Member 1 works mainly in:
```text
extension/
```

Member 2 works mainly in:
```text
privacy/
```

Member 3 works mainly in:
```text
server/
agent/
```

Shared files should not be changed without informing the team.

---

# 13. AI Coding Agent Rules

Every AI coding agent must:
1. Read this file before coding.
2. Follow this API contract.
3. Modify only its assigned module.
4. Do not redesign the architecture.
5. Do not change another member's module.
6. Do not change API formats without team approval.
7. Write tests.
8. Use mock data when necessary.
9. Keep existing functionality working.
10. Report integration problems.

---

# 14. Final Goal

The complete system should work like this:
```text
User Instruction
       |
       v
Browser Extension
       |
       v
Local Privacy AI
       |
       v
Sanitized Data
       |
       v
FastAPI Server
       |
       v
VLM / LLM
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

The main principle is:

> Privacy happens locally before data reaches the server.
