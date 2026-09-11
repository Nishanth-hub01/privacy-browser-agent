# Browser Extension

This folder contains the Chrome/Manifest V3 browser extension for the privacy-preserving browser agent.

## Purpose

- Capture the current page screenshot and DOM
- Collect the user's instruction
- Send the raw context to the local privacy layer
- Send sanitized data only to the backend server
- Receive a structured AI action
- Validate and execute safe browser actions

## Files

- manifest.json: extension manifest and permissions
- popup.html: popup UI for user instructions and status
- popup.js: orchestration between page capture, privacy boundary, server call, and action execution
- src/content.js: content script for DOM extraction and in-page action execution
- src/background.js: background worker for runtime setup and message handling

## Privacy rule

The extension must never send raw screenshot or raw DOM data directly to the server. It must use the privacy module before hitting the backend.

## Local testing

1. Open Chrome and load this unpacked extension from the extension/ folder.
2. Visit a test page.
3. Open the extension popup.
4. Enter a user instruction, then click Analyze page.
5. Confirm the popup shows the server response and, if confidence is high enough, the action can be executed.
