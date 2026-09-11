chrome.runtime.onInstalled.addListener(() => {
  console.log('Privacy browser agent installed.');
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message && message.type === 'ping') {
    sendResponse({ ok: true, tabId: sender.tab ? sender.tab.id : null });
    return true;
  }

  return false;
});
