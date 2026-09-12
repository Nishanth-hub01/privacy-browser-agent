const MESSAGE_TYPES = Object.freeze({
  ANALYZE_PAGE: 'ANALYZE_PAGE',
  CAPTURE_SCREENSHOT: 'CAPTURE_SCREENSHOT',
  GET_PAGE_CONTEXT: 'GET_PAGE_CONTEXT'
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
    Object.values(MESSAGE_TYPES).includes(message.type)
  );
}

function isRestrictedPage(url) {
  try {
    return RESTRICTED_PAGE_PROTOCOLS.has(new URL(url || '').protocol);
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
    throw Object.assign(new Error('This page does not allow extension analysis.'), { code: 'RESTRICTED_PAGE' });
  }

  return tab;
}

function sendToContentScript(tabId, message) {
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

async function handleRequest(message) {
  const tab = await getActiveTab();

  if (message.type === MESSAGE_TYPES.CAPTURE_SCREENSHOT) {
    try {
      const image = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'png' });
      if (!image) throw new Error('The browser returned an empty screenshot.');
      return { ok: true, type: message.type, screenshot: image };
    } catch (error) {
      throw Object.assign(new Error(error.message || 'Screenshot capture failed.'), { code: 'SCREENSHOT_FAILED' });
    }
  }

  const contentMessage = {
    type: message.type === MESSAGE_TYPES.ANALYZE_PAGE ? MESSAGE_TYPES.ANALYZE_PAGE : MESSAGE_TYPES.GET_PAGE_CONTEXT
  };
  const response = await sendToContentScript(tab.id, contentMessage);
  return { ok: true, type: message.type, ...response };
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
