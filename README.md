# On-device Browser Agent

A privacy-aware Chrome browser agent for understanding webpages and carrying out carefully validated browser actions. The project is designed for a Smart India Hackathon demonstration: it combines DOM structure, visible-page screenshots, local sanitization, replaceable perception, backend reasoning, and restricted browser execution.

The goal is not to automate everything. The goal is to show a practical way to make browser assistance more useful while reducing the amount of private page data sent outside the browser.

## Problem Statement

Webpages contain useful controls and large amounts of sensitive information. A conventional browser agent may send raw HTML, screenshots, form values, cookies, or tokens to a remote model. That creates unnecessary privacy and security risk.

Users need an assistant that can:

- Understand the structure and appearance of the current webpage.
- Identify the control relevant to a natural-language instruction.
- Protect sensitive page information before backend communication.
- Execute only a small, validated set of browser actions.
- Explain failures instead of silently taking unsafe actions.

## Proposed Solution

The browser extension acts as a lightweight orchestration layer. It collects compact DOM metadata and a screenshot of the visible tab, applies local privacy rules, runs a replaceable local perception layer, and sends only the sanitized context needed for backend reasoning. The returned action is validated again before it can affect the webpage.

The current repository includes a deterministic mock/local perception implementation so the pipeline can be demonstrated without requiring an online AI service. The backend integration is configurable and can later be connected to a local or hosted reasoning service.

## Architecture

```text
User instruction
      |
      v
Popup UI
      |
      | Chrome runtime messaging
      v
Manifest V3 service worker
      |
      +--> Content script --> DOM analyzer --> compact DOM metadata
      |
      +--> captureVisibleTab --> visible screenshot kept in memory
      |
      v
Local privacy sanitization
      |
      v
Local AI/perception layer
      |
      v
Sanitized JSON context
      |
      v
Configurable backend API
      |
      v
Validated action response
      |
      v
Action executor in content script
      |
      v
Webpage
```

### Module responsibilities

- `extension/popup/`: instruction input, controls, progress, and error status.
- `extension/service-worker.js`: active-tab checks, message routing, orchestration, timeouts, backend communication, and action confidence gating.
- `extension/content/`: page-side message handling and safe action execution.
- `extension/utils/dom-analyzer.js`: compact semantic element metadata and local element identifiers.
- `extension/utils/screenshot.js`: Manifest V3 screenshot wrapper for the visible tab.
- `extension/utils/privacy.js`: deterministic masking of sensitive structured fields and common PII patterns.
- `extension/utils/local-ai.js`: replaceable deterministic perception layer for local testing.
- `extension/utils/api.js`: configurable JSON backend client with timeout and HTTP error handling.
- `extension/utils/action-executor.js`: validation and safe execution of supported actions.
- `server/`: FastAPI schemas, validation, routes, and agent integration.
- `shared/API_CONTRACT.md`: client/server request, response, and validation contract.

## Feature List

### Implemented for demonstration

- Chrome Manifest V3 extension structure.
- Popup instruction input and status updates.
- DOM detection for buttons, links, inputs, textareas, selects, and forms.
- Visibility checks and bounding rectangles.
- Stable page-local identifiers such as `element_1`.
- Visible-tab screenshot capture using `chrome.tabs.captureVisibleTab`.
- Structured privacy sanitization for values, passwords, tokens, cookies, storage fields, emails, and phone numbers.
- Deterministic local/mock perception without an external AI API.
- Configurable JSON backend client.
- Request timeout and network error handling.
- Validation of backend action type, target, URL, values, and confidence.
- Safe action execution for `click`, `type`, `scroll`, `navigate`, and `select`.
- Restricted-page handling for browser-internal pages.
- Structured success and error results.

### Deliberately limited

The current screenshot path captures the visible tab for local perception. A full image-redaction pipeline is not yet implemented, so the integrated backend request uses a redacted screenshot placeholder rather than transmitting the raw screenshot.

## Technology Stack

- **Browser:** Google Chrome with Manifest V3.
- **Extension:** JavaScript, Chrome Extensions APIs, content scripts, service worker, `chrome.tabs`, `chrome.runtime`, and `chrome.scripting` permissions where applicable.
- **Local processing:** JavaScript DOM analysis, deterministic privacy sanitization, and mock/local perception interface.
- **Backend:** Python, FastAPI, Pydantic, and structured JSON APIs.
- **Testing:** Python test suite, documented extension checks, and manual Chrome workflow testing.
- **Communication:** JSON messages inside the extension and JSON over HTTP for the configurable backend API.

No external library is required by the popup interface, and no API key is hardcoded in the extension.

## On-device Visual Perception

The extension captures the currently visible browser tab locally. The screenshot preserves information that DOM metadata cannot fully express, such as:

- Visual layout and spacing.
- Overlapping or modal content.
- Rendered appearance and visual grouping.
- Whether a control is visible in the current viewport.

The screenshot is kept in memory for the local pipeline. In the current integration, it is not uploaded as raw image data because image redaction is not yet available.

## DOM Analysis

The DOM analyzer performs a targeted query for useful interactive elements instead of serializing the entire webpage. It records compact metadata such as:

- Element type and implicit or explicit role.
- Safe labels, placeholders, and names.
- Visibility.
- Approximate viewport rectangle.
- A page-local identifier used by the action executor.

It does not read form values, passwords, cookies, browser history, or web storage contents. DOM metadata provides precise semantic targets; visual perception provides rendered context. These two views complement each other.

## Privacy Explanation

Privacy is enforced before backend communication. The sanitizer:

- Replaces password and generic form `value` fields with `[REDACTED]`.
- Masks authentication tokens, bearer tokens, JWTs, cookies, secrets, API keys, and storage-related fields.
- Masks common email addresses and phone numbers in text.
- Removes URL query strings and fragments where the sanitizer handles URLs.
- Preserves structural metadata needed for browser automation.
- Never reads `localStorage`, `sessionStorage`, cookies, or browser history.
- Does not print page content or sensitive values in workflow status messages.

This is a privacy-preserving design, not a claim of perfect protection. Additional detectors and image redaction are planned before handling broader production scenarios.

## Local AI Concept

`extension/utils/local-ai.js` defines the replaceable interface:

```js
window.localAi.perceive({ screenshot, dom });
```

The current implementation is deterministic and rule-based. It searches sanitized semantic metadata for likely controls such as Login, Search, Submit, Continue, Cancel, and Back, then returns an intent, target identifier, confidence, and source availability.

A future local model can replace this implementation without changing popup messaging or action execution, provided it returns the same structured perception contract. This keeps the demonstration testable offline while leaving room for WebGPU, WebAssembly, ONNX Runtime Web, or another locally hosted model.

## Backend Communication

The API client sends JSON to a configurable placeholder backend URL. It:

1. Validates that context is structured data.
2. Sanitizes the DOM before serialization.
3. Rejects raw HTML DOM input.
4. Uses `fetch` with an abort timeout.
5. Checks HTTP status and JSON validity.
6. Returns useful network and backend errors.

The backend returns a structured action and confidence. The service worker does not execute it immediately: it first checks the response shape, supported action, target information, URL rules, and confidence threshold.

## End-to-end Workflow

```text
1. User enters an instruction in the popup.
2. Popup sends ANALYZE_PAGE to the service worker.
3. Service worker asks the content script for page context.
4. Content script calls the DOM analyzer.
5. Service worker captures the visible tab screenshot.
6. Privacy sanitization runs locally on structured DOM data.
7. Local/mock perception produces a compact observation.
8. API client prepares sanitized JSON for the backend.
9. Backend returns an action response.
10. Service worker validates action type and confidence.
11. Content script passes the action to the action executor.
12. Action executor validates the target and performs a safe DOM operation.
13. Popup displays progress, success, or a useful error.
```

## Browser Action Execution

Only five action categories are supported:

- **Click:** finds a validated local element ID and calls the element's native `.click()` method.
- **Type:** accepts only non-sensitive text controls and dispatches normal `input` and `change` events.
- **Scroll:** allows bounded upward or downward scrolling.
- **Navigate:** permits only `http` and `https` URLs.
- **Select:** requires a real select element and an existing option value.

The executor never evaluates JavaScript received from a server, runs shell commands, uses arbitrary selectors, or bypasses browser security. Password, token, secret, cookie, and session fields are rejected.

## SIH Demo Steps

### Prepare

1. Start the backend if demonstrating backend communication.
2. Open Chrome and visit `chrome://extensions`.
3. Enable **Developer mode**.
4. Click **Load unpacked** and choose the project `extension` folder.
5. Reload the extension after changes.
6. Check the extension's **Errors** section and service worker console.

### Demonstrate the workflow

1. Open a simple normal `https://` webpage with visible buttons and form controls.
2. Open the extension popup.
3. Enter `Find the submit button`.
4. Click **Analyze Page**.
5. Point out the progress states: page structure, screenshot, local perception, sanitized context, validation, and execution.
6. Show that the relevant button is identified by a compact local ID.
7. Demonstrate **Capture Screenshot** separately.
8. Repeat on a page with a password field and explain that values are not collected or transmitted.
9. Try an invalid or missing target and show the structured failure.
10. Open `chrome://extensions` and show that restricted-page analysis is rejected safely.
11. Stop the backend and show that a useful error appears while local screenshot functionality remains available.

### Expected demonstration result

The agent should identify useful page elements, produce compact context, protect sensitive metadata, report backend or restricted-page errors clearly, and execute only a validated browser action. The exact action depends on the page and backend response.

## Known Limitations

- The local AI is a deterministic mock, not a trained vision-language model.
- Full screenshot redaction is not implemented yet; raw screenshots are retained locally and are not sent to the backend in the current integrated flow.
- The backend must be running and configured for the complete online reasoning path.
- Element identifiers are local to the current page lifecycle and can change after DOM replacement or navigation.
- Browser-internal pages such as `chrome://` pages do not allow normal content-script access.
- The action executor supports a deliberately small action set and does not guarantee success on every website framework.
- Manual Chrome testing is still required for visual behavior and browser permission errors.

## Future Enhancements

- Add local screenshot redaction for faces, text regions, and sensitive visual fields.
- Replace rule-based perception with an optional local WebGPU, WebAssembly, or ONNX model.
- Add stronger page-local element identity that survives controlled DOM updates.
- Add explicit user confirmation for sensitive or irreversible actions.
- Add `select` support end to end in the server action schema and planner.
- Add automated browser tests for restricted pages, popup status, and action execution.
- Add model confidence calibration and explainable action previews.
- Add configurable retention limits and a visible privacy audit panel.
- Measure latency, memory, CPU, and model quality on representative pages.

## Repository Guide

```text
extension/       Chrome extension, popup, content script, utilities
server/          FastAPI API, schemas, validators, and routes
agent/           Agent and planner abstractions
privacy/         Privacy-module integration area
shared/          API contract, types, and examples
tests/           Unit, server, privacy, extension, and integration test plans
```

Important references:

- [shared/API_CONTRACT.md](shared/API_CONTRACT.md)
- [tests/TEST_PLAN.md](tests/TEST_PLAN.md)
- [extension/README.md](extension/README.md)

## Project Status

This repository is suitable for a functional SIH prototype demonstration. The core extension flow, structured privacy boundary, configurable backend client, mock local perception, and action validation are present. Production readiness would require stronger image sanitization, model evaluation, broader browser testing, and additional user-consent safeguards.

## License

This project is developed for educational, research, and hackathon purposes.
