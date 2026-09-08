# Privacy-Preserving Vision Browser Agent

A privacy-preserving browser agent that can understand webpages, detect sensitive information locally, sanitize visual and DOM content, and perform browser actions using AI.

The main goal is to allow an AI browser agent to understand complex webpages **without sending the user's private information to the server**.

---

## 🚀 Project Overview

Modern browser technologies such as **WebGPU, WebAssembly, ONNX Runtime Web, and browser extensions** make it possible to run AI models directly inside the user's browser.

Our system uses this capability to build a privacy-first browser agent.

### Basic Workflow

```text
                    WEBPAGE
                       │
                       ▼
             ┌──────────────────┐
             │ Browser Extension│
             │     Member 1     │
             └────────┬─────────┘
                      │
                 Screenshot
                  + DOM
                      │
                      ▼
             ┌──────────────────┐
             │ Local Privacy &  │
             │ Vision AI        │
             │     Member 2     │
             └────────┬─────────┘
                      │
              Sanitized Context
                      │
                      ▼
             ┌──────────────────┐
             │   FastAPI Server │
             │     Member 3     │
             └────────┬─────────┘
                      │
                      ▼
                   VLM / LLM
                      │
                      ▼
                 Action JSON
                      │
                      ▼
             ┌──────────────────┐
             │ Browser Extension│
             └────────┬─────────┘
                      │
                      ▼
                Browser Action
```

---

## 🎯 Objectives

* Understand webpages using visual and DOM information.
* Detect sensitive information locally.
* Redact or mask private information before transmission.
* Ensure raw sensitive data never reaches the server.
* Use a server-side VLM/LLM for complex reasoning.
* Convert AI decisions into structured browser actions.
* Execute actions automatically through the browser extension.
* Maintain a balance between privacy, accuracy, latency, and resource usage.

---

## 🔐 Privacy Principle

The most important rule of this project is:

> **Raw user data must never be sent to the server.**

The processing pipeline is:

```text
Raw Screen
    ↓
Local Privacy Detection
    ↓
Sensitive Data Detection
    ↓
Redaction / Masking
    ↓
Privacy Verification
    ↓
Sanitized Screen + DOM
    ↓
Server
```

Sensitive information may include:

* Passwords
* Email addresses
* Phone numbers
* Government IDs
* Credit/debit card numbers
* Faces
* Sensitive form fields
* Personal names
* Private DOM elements

---

## 🧩 Project Structure

```text
privacy-browser-agent/
│
├── extension/
│   ├── manifest.json
│   ├── src/
│   └── README.md
│
├── privacy/
│   ├── src/
│   ├── models/
│   └── README.md
│
├── server/
│   ├── app/
│   ├── models/
│   └── README.md
│
├── shared/
│   ├── API_CONTRACT.md
│   ├── types.ts
│   └── examples/
│       ├── extension-input.json
│       ├── privacy-output.json
│       └── server-response.json
│
├── tests/
│   ├── privacy/
│   ├── extension/
│   ├── server/
│   └── integration/
│
├── README.md
└── .gitignore
```

---

## 👥 Team Responsibilities

### Member 1 — Browser Extension

Responsible for:

* Chrome/Firefox extension
* Manifest V3
* Screenshot capture
* DOM extraction
* User instructions
* Communication with privacy module
* Communication with server
* Receiving action commands
* Executing browser actions

Technologies:

* JavaScript / TypeScript
* Chrome Extension APIs
* Firefox Extension APIs
* Manifest V3

---

### Member 2 — Local Privacy + Vision AI

Responsible for:

* Sensitive information detection
* PII detection
* Password detection
* Face detection
* Screenshot redaction
* DOM sanitization
* Privacy verification
* Local AI inference

Technologies:

* JavaScript / TypeScript
* ONNX Runtime Web
* WebGPU
* WebAssembly
* Transformers.js
* Computer Vision models

---

### Member 3 — Server + AI

Responsible for:

* FastAPI backend
* API endpoints
* VLM/LLM integration
* AI reasoning
* Action planning
* Returning structured action JSON
* Server-side validation
* Integration support

Technologies:

* Python
* FastAPI
* Pydantic
* VLM / LLM
* HTTP APIs

---

## 🔄 Data Flow

### 1. Extension → Privacy

The extension collects:

```text
Screenshot
DOM
Current URL
User Instruction
```

Example:

```json
{
  "request_id": "req-001",
  "url": "https://example.com",
  "screenshot": "<BASE64_IMAGE>",
  "dom": "<HTML_CONTENT>",
  "user_instruction": "Find the submit button"
}
```

---

### 2. Privacy Processing

The local privacy engine:

```text
Detect sensitive information
        ↓
Redact sensitive information
        ↓
Sanitize DOM
        ↓
Verify privacy
```

Example:

```text
John Smith
john@example.com
Password: ********

        ↓

[PERSON]
[EMAIL]
Password: [REDACTED]
```

---

### 3. Privacy → Server

Only sanitized information is sent:

```json
{
  "request_id": "req-001",
  "user_instruction": "Find the submit button",
  "sanitized_screenshot": "<BASE64_IMAGE>",
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

### 4. Server → AI

The server sends the sanitized context to the VLM/LLM.

The AI determines:

```text
What does the user want?
        ↓
What webpage element is relevant?
        ↓
What action should be performed?
```

---

### 5. Server → Extension

The server returns structured action JSON:

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
  "reason": "The Submit button matches the user's requested action."
}
```

---

### 6. Extension Executes Action

The extension receives the action and performs:

```text
click
scroll
type
navigate
```

Only safe, validated actions should be executed.

---

## 🛠️ Technology Stack

### Frontend / Extension

* TypeScript
* JavaScript
* Chrome Extension API
* Firefox Extension API
* Manifest V3

### Local AI

* ONNX Runtime Web
* WebGPU
* WebAssembly
* Transformers.js
* Computer Vision / Vision Transformer models

### Backend

* Python
* FastAPI
* Pydantic
* HTTPX / Requests

### AI

* Vision-Language Model
* Large Language Model
* Open-weight or API-based models

### Development

* VS Code
* Git
* GitHub
* Chrome
* Firefox
* Google Colab

---

## 📊 Evaluation Metrics

The project will be evaluated using:

| Metric                                     | Weight |
| ------------------------------------------ | -----: |
| Visual Context Accuracy                    |    25% |
| Sensitive/PII Detection Precision & Recall |    20% |
| Redaction Precision                        |    20% |
| Client Resource Utilization                |    20% |
| End-to-End Latency                         |    15% |

---

## 🧪 Development Strategy

We will develop the system incrementally.

### Phase 1 — Basic Extension

```text
Extension
   ↓
Capture Screenshot
   ↓
Extract DOM
```

### Phase 2 — Local Privacy

```text
Screenshot + DOM
       ↓
Privacy Engine
       ↓
Detect PII
       ↓
Redact PII
```

### Phase 3 — Backend

```text
Sanitized Data
       ↓
FastAPI
       ↓
Mock AI
       ↓
Action JSON
```

### Phase 4 — Browser Action

```text
Action JSON
     ↓
Extension
     ↓
Click / Scroll / Navigate
```

### Phase 5 — Real AI

Replace mock AI with a VLM/LLM.

### Phase 6 — Optimization

Measure and improve:

* Accuracy
* Privacy detection
* Redaction quality
* Latency
* CPU usage
* RAM usage
* GPU usage

---

## 🔗 API Contract

All team members must follow:

```text
shared/API_CONTRACT.md
```

This file defines communication between:

```text
Extension ↔ Privacy
Privacy ↔ Server
Server ↔ Extension
```

### Important Rule

> Do not change the shared API format without informing the entire team.

---

## 🌿 Git Branch Strategy

```text
main
│
├── feature/extension
├── feature/privacy
└── feature/server-ai
```

Optional integration branch:

```text
main
│
├── feature/extension
├── feature/privacy
├── feature/server-ai
│
└── integration
```

### Rules

* `main` should remain stable.
* Each member works on their own branch.
* Do not directly push development code to `main`.
* Test before creating a Pull Request.
* Review changes before merging.

---

## 💻 Development Workflow

Before starting work:

```bash
git checkout main
git pull origin main
git checkout YOUR-BRANCH
git merge main
```

Work only on your assigned module.

Then:

```bash
git status
git diff
git add .
git commit -m "Describe your change"
git push origin YOUR-BRANCH
```

Create a Pull Request when the feature is ready.

---

## 🤖 AI Coding Agent Rules

AI coding agents can be used to implement each module.

However, every AI agent must follow these rules:

```text
1. Read shared/API_CONTRACT.md first.
2. Modify only the assigned module.
3. Do not redesign the project architecture.
4. Do not change another member's module.
5. Do not change shared API formats without approval.
6. Write tests for implemented functionality.
7. Follow existing project structure.
8. Report integration problems instead of silently changing contracts.
```

---

## 🧪 Testing

Testing will happen at multiple levels.

### Unit Tests

Test individual components:

```text
PII detection
Redaction
DOM sanitization
API validation
Action validation
```

### Integration Tests

Test:

```text
Extension → Privacy
Privacy → Server
Server → Extension
```

### End-to-End Test

Complete flow:

```text
User Instruction
      ↓
Browser Extension
      ↓
Local Privacy AI
      ↓
Sanitized Context
      ↓
Server
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

## 🎬 Example Use Case

Suppose a webpage contains:

```text
Name: John Smith
Email: john@example.com
Password: ********

Upload your document

[Upload Document]
```

The user says:

```text
"Find where I can upload my document."
```

The extension captures the webpage.

The local privacy engine detects private information:

```text
John Smith       → [PERSON]
john@example.com → [EMAIL]
Password         → [REDACTED]
```

Only the sanitized context is sent to the server.

The VLM understands that the relevant action is:

```json
{
  "type": "click",
  "target": {
    "id": "upload-button"
  }
}
```

The extension executes the click.

### Result

The AI can understand and interact with the webpage **without exposing the user's private information to the server**.

---

## 🔒 Security Requirements

The system must:

* Never send raw screenshots containing sensitive data.
* Never send passwords to the server.
* Never send unredacted PII.
* Validate sanitized data before transmission.
* Validate AI-generated actions before execution.
* Prevent unsafe or unauthorized browser actions.
* Log privacy violations during development.
* Avoid storing sensitive user information unnecessarily.

---

## 🚧 Current Development Status

```text
[X] Repository setup
[X] Folder structure
[X] API contract
[ ] Shared TypeScript/Pydantic schemas
[ ] Browser extension
[ ] Screenshot capture
[ ] DOM extraction
[ ] Local privacy engine
[ ] PII detection
[ ] Screenshot redaction
[ ] DOM sanitization
[ ] FastAPI server
[ ] VLM/LLM integration
[ ] Action execution
[ ] Integration testing
[ ] Performance testing
[ ] Privacy evaluation
[ ] Final demonstration
```

---

## 🎯 Final Goal

Build a browser agent that can:

```text
UNDERSTAND
    ↓
PROTECT
    ↓
REASON
    ↓
ACT
```

while ensuring:

> **Privacy is enforced locally before any information leaves the user's browser.**

---

## 📄 License

This project is developed for educational, research, and hackathon purposes.
