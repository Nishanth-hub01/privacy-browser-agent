# Browser Agent API Contract

Version: 1.0.0

This document defines the client/server contract only. It does not implement the backend.

## Endpoint

```text
POST /analyze
Content-Type: application/json
```

The client sends only locally sanitized context. Raw passwords, cookies, storage data,
authentication tokens, and unsanitized DOM must never be included.

## Request

Required fields:

```json
{
  "request_id": "req-001",
  "dom": {
    "page": {
      "title": "Example page",
      "url": "https://example.test/account"
    },
    "elements": []
  }
}
```

Required fields:

- `request_id`: non-empty client-generated string.
- `dom`: sanitized structured DOM metadata. Raw HTML is not accepted.

Optional fields:

- `screenshot`: sanitized screenshot data as a data URL or supported encoded image.
- `user_instruction`: user-provided task description after local sanitization.
- `timestamp`: ISO 8601 request timestamp.

The DOM may contain useful element metadata such as local element IDs, type, role,
text labels, visibility, and bounding rectangles. It must not contain control values,
passwords, tokens, cookies, `localStorage`, or `sessionStorage` contents.

## Success Response

```json
{
  "request_id": "req-001",
  "status": "success",
  "action": "click",
  "target": "element_1",
  "confidence": 0.95,
  "reason": "The primary action matches the request."
}
```

Required response fields:

- `request_id`: matches the request.
- `status`: `success`.
- `action`: one supported action name.
- `target`: local element identifier, except where noted below.

Optional response fields:

- `text`: required for `type`.
- `direction` and `amount`: required for `scroll`.
- `url`: required for `navigate` and must be an `http` or `https` URL.
- `value`: required for `select`; it identifies the option to select and must not
  contain a secret.
- `confidence`: number from `0.0` to `1.0`.
- `reason`: concise explanation without private data.

## Supported Actions

### Click

```json
{
  "action": "click",
  "target": "element_1"
}
```

### Type

```json
{
  "action": "type",
  "target": "element_2",
  "text": "example"
}
```

The server must never request typing a password, authentication token, or other
sensitive value.

### Scroll

```json
{
  "action": "scroll",
  "direction": "down",
  "amount": 600
}
```

`direction` must be `up` or `down`. `amount` must be a positive finite number.
The `target` may be omitted for page-level scrolling.

### Navigate

```json
{
  "action": "navigate",
  "target": "element_4",
  "url": "https://example.test/next"
}
```

`url` must use `http` or `https`. The client must reject other protocols.

### Select

```json
{
  "action": "select",
  "target": "element_5",
  "value": "option-a"
}
```

`value` identifies a non-sensitive option. It must not be used to transmit form
secrets.

## Validation Rules

The client must reject responses when:

- JSON is invalid or the response is not an object.
- `status` is not `success` or `error`.
- `action` is not `click`, `type`, `scroll`, `navigate`, or `select`.
- `target` is missing or is not a local element identifier when required.
- `type` has no non-empty string `text`.
- `scroll` has an invalid direction or non-positive amount.
- `navigate` has an invalid or non-HTTP(S) URL.
- `select` has no non-empty option `value`.
- `confidence` is outside the range `0.0` to `1.0`.
- Any response field contains a password, token, cookie, or other secret.

The client should not execute actions below its configured confidence threshold. A
common initial threshold is `0.80`.

## Error Response

Errors use HTTP 4xx for invalid client requests and HTTP 5xx for server failures:

```json
{
  "request_id": "req-001",
  "status": "error",
  "error": {
    "code": "INVALID_CONTEXT",
    "message": "The sanitized DOM context is invalid."
  }
}
```

Required error fields:

- `status`: `error`.
- `error.code`: stable machine-readable code.
- `error.message`: safe human-readable message without secrets.

Recommended error codes:

- `INVALID_REQUEST`
- `INVALID_CONTEXT`
- `PRIVACY_CHECK_FAILED`
- `ACTION_NOT_FOUND`
- `LOW_CONFIDENCE`
- `MODEL_ERROR`
- `SERVER_ERROR`

Error messages must never echo request bodies, passwords, cookies, storage values,
authentication tokens, or other sensitive information.

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
