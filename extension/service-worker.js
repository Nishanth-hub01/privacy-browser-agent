importScripts('utils/privacy.js', 'utils/local-ai.js', 'utils/api.js');

const MESSAGE_TYPES = Object.freeze({
  ANALYZE_PAGE: 'ANALYZE_PAGE',
  CAPTURE_SCREENSHOT: 'CAPTURE_SCREENSHOT',
  GET_PAGE_CONTEXT: 'GET_PAGE_CONTEXT',
  EXECUTE_ACTION: 'EXECUTE_ACTION',
  WORKFLOW_STATUS: 'WORKFLOW_STATUS'
});

const CONTENT_SCRIPT_TIMEOUT_MS = 5000;
const RESTRICTED_PAGE_PROTOCOLS = new Set(['chrome:', 'chrome-extension:', 'edge:', 'about:', 'devtools:']);

function createError(message, code = 'REQUEST_FAILED') {
  return { ok: false, error: { code, message } };
}

function isValidMessage(message) {
  return Boolean(
    message &&
    typeof message === 'object' &&
    [MESSAGE_TYPES.ANALYZE_PAGE, MESSAGE_TYPES.CAPTURE_SCREENSHOT, MESSAGE_TYPES.GET_PAGE_CONTEXT, MESSAGE_TYPES.EXECUTE_ACTION].includes(message.type)
  );
}

function emitStatus(message) {
  chrome.runtime.sendMessage({ type: MESSAGE_TYPES.WORKFLOW_STATUS, message }, () => {
    void chrome.runtime.lastError;
  });
}

function isRestrictedPage(url) {
  try {
    const parsed = new URL(url || '');
    if (RESTRICTED_PAGE_PROTOCOLS.has(parsed.protocol)) return true;
    if (parsed.hostname === 'chromewebstore.google.com' || parsed.hostname === 'chrome.google.com') return true;
    return false;
  } catch (error) {
    return true;
  }
}

async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  const tab = tabs[0];

  if (!tab || typeof tab.id !== 'number') {
    throw Object.assign(new Error('No active browser tab is available.'), { code: 'NO_ACTIVE_TAB' });
  }

  if (isRestrictedPage(tab.url)) {
    throw Object.assign(new Error('This page does not allow extension analysis (internal browser page or Chrome Web Store). Please switch to a standard webpage.'), { code: 'RESTRICTED_PAGE' });
  }

  return tab;
}

function rawSendMessage(tabId, message) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const timeoutId = setTimeout(() => {
      if (!settled) {
        settled = true;
        reject(Object.assign(new Error('The page did not respond in time.'), { code: 'CONTENT_TIMEOUT' }));
      }
    }, CONTENT_SCRIPT_TIMEOUT_MS);

    chrome.tabs.sendMessage(tabId, message, (response) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeoutId);

      if (chrome.runtime.lastError) {
        reject(Object.assign(new Error(chrome.runtime.lastError.message), { code: 'CONTENT_UNAVAILABLE' }));
        return;
      }

      if (!response || response.ok === false) {
        reject(Object.assign(new Error(response?.error?.message || response?.error || 'The content script rejected the request.'), { code: 'CONTENT_ERROR' }));
        return;
      }

      resolve(response);
    });
  });
}

async function sendToContentScript(tabId, message) {
  try {
    return await rawSendMessage(tabId, message);
  } catch (error) {
    const msg = String(error?.message || '');
    if (msg.includes('Could not establish connection') || msg.includes('Receiving end does not exist')) {
      // Content script was not yet injected (e.g., page was loaded before the extension was loaded/reloaded)
      if (chrome.scripting && typeof chrome.scripting.executeScript === 'function') {
        try {
          await chrome.scripting.executeScript({
            target: { tabId },
            files: [
              'utils/dom-analyzer.js',
              'utils/action-executor.js',
              'content/content-script.js'
            ]
          });
          // Allow script initialization
          await new Promise((resolve) => setTimeout(resolve, 150));
          return await rawSendMessage(tabId, message);
        } catch (injectError) {
          // Injection failed (e.g. restricted or special page)
        }
      }
      throw Object.assign(
        new Error('Could not connect to page scripts. Please refresh this webpage tab (F5 or Ctrl+R) and try again.'),
        { code: 'CONTENT_UNAVAILABLE' }
      );
    }
    throw error;
  }
}

async function handleRequest(message) {
  const tab = await getActiveTab();

  if (message.type === MESSAGE_TYPES.CAPTURE_SCREENSHOT) {
    emitStatus('Capturing visible page...');
    try {
      const image = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'png' });
      if (!image) throw new Error('The browser returned an empty screenshot.');
      return { ok: true, type: message.type, screenshot: image };
    } catch (error) {
      throw Object.assign(new Error(error.message || 'Screenshot capture failed.'), { code: 'SCREENSHOT_FAILED' });
    }
  }

  if (message.type === MESSAGE_TYPES.GET_PAGE_CONTEXT) {
    emitStatus('Reading page structure...');
    const response = await sendToContentScript(tab.id, { type: MESSAGE_TYPES.GET_PAGE_CONTEXT });
    return { ok: true, type: message.type, ...response };
  }

  if (message.type === MESSAGE_TYPES.EXECUTE_ACTION) {
    emitStatus('Executing validated action...');
    const response = await sendToContentScript(tab.id, {
      type: MESSAGE_TYPES.EXECUTE_ACTION,
      action: message.action
    });
    return { ok: true, type: message.type, ...response };
  }

  emitStatus('Reading page structure...');
  const pageResponse = await sendToContentScript(tab.id, { type: MESSAGE_TYPES.GET_PAGE_CONTEXT });
  emitStatus('Capturing visible page...');
  const screenshot = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'png' });
  if (!screenshot) throw Object.assign(new Error('The browser returned an empty screenshot.'), { code: 'SCREENSHOT_FAILED' });

  const dom = pageResponse.data || {};
  const sanitizedDom = privacySanitizer.sanitize(dom);
  emitStatus('Running local perception...');
  const perception = localAi.perceive({ screenshot, dom: sanitizedDom });
  emitStatus('Sending sanitized context...');
  const backendResponse = await browserAgentApi.sendContextToBackend({
    request_id: `req-${Date.now()}`,
    screenshot,
    sanitized_screenshot: '[REDACTED_SCREENSHOT]',
    dom: sanitizedDom,
    user_instruction: typeof message.instruction === 'string' ? message.instruction : ''
  });
  const action = normalizeServerAction(backendResponse);
  validateServerAction(backendResponse, action);
  emitStatus('Validating action...');
  const execution = await sendToContentScript(tab.id, {
    type: MESSAGE_TYPES.EXECUTE_ACTION,
    action
  });
  if (!execution.data || execution.data.success !== true) {
    throw Object.assign(new Error(execution.data?.error?.message || 'Action execution was rejected.'), { code: 'EXECUTION_FAILED' });
  }
  return {
    ok: true,
    type: message.type,
    data: sanitizedDom,
    perception,
    action,
    execution
  };
}

function normalizeServerAction(response) {
  const serverAction = response && response.action;
  if (!serverAction || typeof serverAction !== 'object') return null;

  const type = serverAction.type || serverAction.action;
  const target = serverAction.target;
  const normalized = { action: type };

  if (typeof target === 'string') normalized.target = target;
  if (target && typeof target === 'object' && typeof target.id === 'string') normalized.target = target.id;
  if (type === 'type') normalized.text = serverAction.text;
  if (type === 'scroll') {
    normalized.direction = target && target.direction;
    normalized.amount = target && target.amount;
  }
  if (type === 'navigate') normalized.url = target && target.url;
  if (type === 'select') normalized.value = serverAction.value;
  return normalized;
}

function validateServerAction(response, action) {
  if (!response || response.status !== 'success' || !action) {
    throw Object.assign(new Error('Backend returned no executable action.'), { code: 'INVALID_ACTION_RESPONSE' });
  }
  if (typeof response.confidence !== 'number' || response.confidence < 0.8) {
    throw Object.assign(new Error('Action confidence is below the execution threshold.'), { code: 'LOW_CONFIDENCE' });
  }
  if (!['click', 'type', 'scroll', 'navigate', 'select'].includes(action.action)) {
    throw Object.assign(new Error('Backend returned an unsupported action.'), { code: 'UNSUPPORTED_ACTION' });
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!isValidMessage(message)) {
    sendResponse(createError('Invalid or missing message type.', 'INVALID_MESSAGE'));
    return false;
  }

  handleRequest(message)
    .then(sendResponse)
    .catch((error) => sendResponse(createError(error.message || 'Request failed.', error.code || 'REQUEST_FAILED')));

  return true;
});
