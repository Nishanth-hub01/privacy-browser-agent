(() => {
  const MAX_ELEMENTS = 200;
  const MAX_TEXT_LENGTH = 160;
  const elementIds = new WeakMap();
  let nextElementId = 1;

  const candidateSelector = [
    'button',
    'a',
    'input:not([type="hidden"])',
    'textarea',
    'select',
    'form'
  ].join(',');

  function compactText(value) {
    const text = String(value || '').replace(/\s+/g, ' ').trim();
    return text.length > MAX_TEXT_LENGTH
      ? `${text.slice(0, MAX_TEXT_LENGTH - 1)}...`
      : text;
  }

  function getLocalId(element) {
    let id = elementIds.get(element);
    if (!id) {
      id = `element_${nextElementId}`;
      nextElementId += 1;
      elementIds.set(element, id);
    }
    return id;
  }

  function getImplicitRole(element) {
    const tagName = element.tagName.toLowerCase();
    if (tagName === 'a') return 'link';
    if (tagName === 'button') return 'button';
    if (tagName === 'textarea') return 'textbox';
    if (tagName === 'select') return 'combobox';

    if (tagName === 'input') {
      const inputType = (element.getAttribute('type') || 'text').toLowerCase();
      if (inputType === 'checkbox') return 'checkbox';
      if (inputType === 'radio') return 'radio';
      if (inputType === 'range') return 'slider';
      if (inputType === 'submit' || inputType === 'reset' || inputType === 'button') {
        return 'button';
      }
      return 'textbox';
    }

    return null;
  }

  function isVisible(element) {
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

  function getRect(element) {
    const rect = element.getBoundingClientRect();
    return {
      x: Math.round(rect.left),
      y: Math.round(rect.top),
      width: Math.round(rect.width),
      height: Math.round(rect.height)
    };
  }

  function getSafeText(element) {
    const tagName = element.tagName.toLowerCase();
    if (tagName !== 'button' && tagName !== 'a') return null;
    return compactText(element.innerText);
  }

  function getElementMetadata(element) {
    const tagName = element.tagName.toLowerCase();
    const metadata = {
      id: getLocalId(element),
      type: tagName,
      role: element.getAttribute('role') || getImplicitRole(element),
      visible: isVisible(element),
      rect: getRect(element)
    };

    const text = getSafeText(element);
    const ariaLabel = compactText(element.getAttribute('aria-label'));
    const placeholder = compactText(element.getAttribute('placeholder'));
    const name = compactText(element.getAttribute('name'));
    const domId = compactText(element.getAttribute('id'));

    if (text) metadata.text = text;
    if (ariaLabel) metadata.ariaLabel = ariaLabel;
    if (placeholder) metadata.placeholder = placeholder;
    if (name) metadata.name = name;
    if (domId) metadata.domId = domId;

    return metadata;
  }

  function getSafePageUrl() {
    return `${location.origin}${location.pathname}`;
  }

  function analyze() {
    const candidates = document.querySelectorAll(candidateSelector);
    const elements = [];
    const limit = Math.min(candidates.length, MAX_ELEMENTS);

    for (let index = 0; index < limit; index += 1) {
      elements.push(getElementMetadata(candidates[index]));
    }

    return {
      page: {
        title: compactText(document.title),
        url: getSafePageUrl()
      },
      elements
    };
  }

  window.domAnalyzer = Object.freeze({ analyze });
})();
