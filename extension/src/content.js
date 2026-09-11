function collectVisualElements() {
  const candidates = Array.from(document.querySelectorAll('button, a, input, textarea, select, [role="button"], [role="link"], [onclick]'));

  return candidates.slice(0, 25).map((element) => {
    const label = (element.textContent || element.getAttribute('aria-label') || element.getAttribute('placeholder') || element.getAttribute('value') || '').trim();

    return {
      type: element.tagName.toLowerCase(),
      label: label || undefined,
      id: element.id || undefined,
      selector: element.id ? '#' + CSS.escape(element.id) : undefined
    };
  });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.type) {
    sendResponse({ ok: false, reason: 'No message type provided.' });
    return false;
  }

  if (message.type === 'collect-page') {
    const payload = {
      url: location.href,
      dom: document.documentElement.outerHTML,
      visualElements: collectVisualElements()
    };
    sendResponse(payload);
    return true;
  }

  if (message.type === 'execute-action') {
    const action = message.action || {};

    if (action.type === 'click') {
      const target = action.target || {};
      const selector = target.id ? '#' + CSS.escape(target.id) : target.selector;
      const element = selector ? document.querySelector(selector) : null;
      if (element) element.click();
      sendResponse({ ok: true, executed: true });
      return true;
    }

    if (action.type === 'scroll') {
      const direction = action.target && action.target.direction === 'up' ? -1 : 1;
      const amount = Number(action.target && action.target.amount) || 300;
      window.scrollBy({ top: direction * amount, left: 0, behavior: 'smooth' });
      sendResponse({ ok: true, executed: true });
      return true;
    }

    if (action.type === 'type') {
      const target = action.target || {};
      const selector = target.id ? '#' + CSS.escape(target.id) : target.selector;
      const element = selector ? document.querySelector(selector) : null;
      if (element && 'value' in element) {
        element.focus();
        element.value = action.text || '';
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
      }
      sendResponse({ ok: true, executed: true });
      return true;
    }

    if (action.type === 'navigate') {
      const url = action.target && action.target.url;
      if (url) {
        window.location.href = url;
      }
      sendResponse({ ok: true, executed: true });
      return true;
    }

    sendResponse({ ok: false, reason: 'Unsupported action type' });
    return true;
  }

  sendResponse({ ok: false, reason: 'Unknown message type.' });
  return false;
});
