(() => {
  const MAX_TEXT_LENGTH = 160;
  const MAX_ELEMENTS = 100;
  const MAX_VISIBLE_TEXT_ITEMS = 100;
  const INPUT_SELECTOR = 'input:not([type="hidden"]), textarea, select';
  const ELEMENT_SELECTOR = [
    'button',
    'a',
    INPUT_SELECTOR,
    'form',
    '[role="button"]',
    '[role="link"]'
  ].join(', ');

  function isElementVisible(element) {
    if (!(element instanceof Element)) return false;

    const style = window.getComputedStyle(element);
    if (
      style.display === 'none' ||
      style.visibility === 'hidden' ||
      style.visibility === 'collapse' ||
      style.opacity === '0'
    ) {
      return false;
    }

    const rect = element.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function compactText(value) {
    const text = String(value || '').replace(/\s+/g, ' ').trim();
    return text.length > MAX_TEXT_LENGTH
      ? `${text.slice(0, MAX_TEXT_LENGTH - 1)}...`
      : text;
  }

  function addOptionalMetadata(metadata, key, value) {
    const compactValue = compactText(value);
    if (compactValue) metadata[key] = compactValue;
  }

  function getPosition(element) {
    const rect = element.getBoundingClientRect();
    return {
      x: Math.round(rect.left),
      y: Math.round(rect.top),
      width: Math.round(rect.width),
      height: Math.round(rect.height)
    };
  }

  function getElementMetadata(element) {
    const tagName = element.tagName.toLowerCase();
    const metadata = {
      type: tagName,
      position: getPosition(element)
    };

    addOptionalMetadata(metadata, 'id', element.id);
    addOptionalMetadata(metadata, 'name', element.getAttribute('name'));
    addOptionalMetadata(metadata, 'placeholder', element.getAttribute('placeholder'));
    addOptionalMetadata(metadata, 'ariaLabel', element.getAttribute('aria-label'));
    addOptionalMetadata(metadata, 'role', element.getAttribute('role'));

    if (tagName === 'input') {
      addOptionalMetadata(metadata, 'inputType', element.getAttribute('type') || 'text');
    }

    if (tagName === 'button' || tagName === 'a' || tagName === 'form') {
      addOptionalMetadata(metadata, 'text', element.innerText);
    }

    return metadata;
  }

  function collectElements() {
    return Array.from(document.querySelectorAll(ELEMENT_SELECTOR))
      .filter(isElementVisible)
      .slice(0, MAX_ELEMENTS)
      .map(getElementMetadata);
  }

  function collectVisibleText() {
    const textItems = [];
    const seen = new Set();
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;

    while (textItems.length < MAX_VISIBLE_TEXT_ITEMS && (node = walker.nextNode())) {
      const parent = node.parentElement;
      if (!parent || !isElementVisible(parent)) continue;
      if (parent.closest('script, style, noscript, template, input, textarea, select, option')) {
        continue;
      }

      const text = compactText(node.nodeValue);
      if (text && !seen.has(text)) {
        seen.add(text);
        textItems.push(text);
      }
    }

    return textItems;
  }

  function analyzeDom() {
    if (!document.body) {
      return { elements: [], visibleText: [] };
    }

    return {
      elements: collectElements(),
      visibleText: collectVisibleText()
    };
  }

  function sendError(sendResponse, error) {
    const reason = error instanceof Error ? error.message : 'DOM analysis failed.';
    sendResponse({ ok: false, error: reason });
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!message || (message.type !== 'analyze-dom' && message.type !== 'collect-page')) {
      return false;
    }

    try {
      sendResponse({ ok: true, data: analyzeDom() });
    } catch (error) {
      sendError(sendResponse, error);
    }

    return true;
  });
})();
