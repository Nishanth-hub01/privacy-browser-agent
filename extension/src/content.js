function getElementText(element) {
  const text = element.textContent || '';
  const ariaLabel = element.getAttribute('aria-label') || '';
  const placeholder = element.getAttribute('placeholder') || '';
  const value = element.getAttribute('value') || '';
  const combined = [text, ariaLabel, placeholder, value].join(' ');
  return combined.replace(/\s+/g, ' ').trim();
}

function buildSelector(element) {
  if (!element || !(element instanceof Element)) return null;

  if (element.id) {
    return '#' + CSS.escape(element.id);
  }

  const tagName = element.tagName.toLowerCase();
  if (element.name) {
    return `${tagName}[name="${CSS.escape(element.name)}"]`;
  }

  if (element.classList && element.classList.length) {
    const className = Array.from(element.classList)
      .filter(Boolean)
      .slice(0, 3)
      .map((classItem) => `.${CSS.escape(classItem)}`)
      .join('');

    if (className) {
      return `${tagName}${className}`;
    }
  }

  return tagName;
}

function isVisible(element) {
  if (!element || !(element instanceof Element)) return false;

  const style = window.getComputedStyle(element);
  if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
    return false;
  }

  const rect = element.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0;
}

function collectVisualElements() {
  const selector = [
    'button',
    'a',
    'input:not([type="hidden"])',
    'textarea',
    'select',
    '[role="button"]',
    '[role="link"]',
    'summary',
    '[onclick]'
  ].join(', ');

  const candidates = Array.from(document.querySelectorAll(selector));

  return candidates
    .filter((element) => isVisible(element))
    .slice(0, 25)
    .map((element) => {
      const label = getElementText(element);
      const rect = element.getBoundingClientRect();

      return {
        type: element.tagName.toLowerCase(),
        label: label || undefined,
        id: element.id || undefined,
        selector: buildSelector(element) || undefined,
        x: Math.round(rect.left),
        y: Math.round(rect.top),
        width: Math.max(0, Math.round(rect.width)),
        height: Math.max(0, Math.round(rect.height))
      };
    });
}

function collectPageSnapshot() {
  return {
    url: location.href,
    title: document.title || '',
    dom: document.documentElement.outerHTML,
    visualElements: collectVisualElements()
  };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.type) {
    sendResponse({ ok: false, reason: 'No message type provided.' });
    return false;
  }

  if (message.type === 'collect-page') {
    const payload = collectPageSnapshot();
    sendResponse({ ok: true, ...payload });
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
