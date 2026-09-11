const EXTENSION_NAME = 'Privacy Browser Agent';

chrome.runtime.onInstalled.addListener(() => {
  console.log(`${EXTENSION_NAME} installed.`);
  chrome.storage.local.set({
    privacyBrowserAgent: {
      installedAt: Date.now(),
      version: chrome.runtime.getManifest().version,
      status: 'ready'
    }
  });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.type) {
    sendResponse({ ok: false, reason: 'No message type provided.' });
    return false;
  }

  if (message.type === 'ping') {
    sendResponse({ ok: true, tabId: sender.tab ? sender.tab.id : null });
    return true;
  }

  if (message.type === 'collect-page') {
    if (!sender.tab || !sender.tab.id) {
      sendResponse({ ok: false, reason: 'No active tab available.' });
      return false;
    }

    chrome.tabs.sendMessage(sender.tab.id, { type: 'collect-page' }, (response) => {
      if (chrome.runtime.lastError) {
        sendResponse({ ok: false, reason: chrome.runtime.lastError.message });
        return;
      }

      sendResponse({ ok: true, ...response });
    });

    return true;
  }

  if (message.type === 'execute-action') {
    if (!sender.tab || !sender.tab.id) {
      sendResponse({ ok: false, reason: 'No active tab available.' });
      return false;
    }

    chrome.tabs.sendMessage(sender.tab.id, { type: 'execute-action', action: message.action }, (response) => {
      if (chrome.runtime.lastError) {
        sendResponse({ ok: false, reason: chrome.runtime.lastError.message });
        return;
      }

      sendResponse({ ok: true, ...response });
    });

    return true;
  }

  sendResponse({ ok: false, reason: 'Unknown message type.' });
  return false;
});
