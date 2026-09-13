(() => {
  const MAX_SCROLL_AMOUNT = 2000;
  const ELEMENT_SELECTOR = [
    'button',
    'a',
    'input:not([type="hidden"])',
    'textarea',
    'select',
    'form'
  ].join(',');
  const SENSITIVE_NAME_PATTERN = /password|passcode|passwd|token|secret|auth|cookie|session/i;
  const SUPPORTED_ACTIONS = new Set(['click', 'type', 'scroll', 'navigate', 'select']);

  function resultError(action, target, code, message) {
    return {
      success: false,
      action: action || null,
      target: target || null,
      error: { code, message }
    };
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

  function findTarget(identifier) {
    if (typeof identifier !== 'string' || !/^element_[1-9]\d*$/.test(identifier)) {
      return null;
    }

    const index = Number(identifier.slice('element_'.length)) - 1;
    const candidates = Array.from(document.querySelectorAll(ELEMENT_SELECTOR)).slice(0, 200);
    return candidates[index] || null;
  }

  function isSensitiveField(element) {
    const type = (element.getAttribute('type') || '').toLowerCase();
    const metadata = [
      type,
      element.getAttribute('name'),
      element.getAttribute('id'),
      element.getAttribute('aria-label'),
      element.getAttribute('placeholder')
    ].filter(Boolean).join(' ');
    return type === 'password' || SENSITIVE_NAME_PATTERN.test(metadata);
  }

  function validateAction(input) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) {
      return { error: resultError(null, null, 'INVALID_ACTION', 'Action must be an object.') };
    }

    const action = typeof input.action === 'string' ? input.action.trim().toLowerCase() : '';
    const target = input.target;
    if (!SUPPORTED_ACTIONS.has(action)) {
      return { error: resultError(action, target, 'UNSUPPORTED_ACTION', 'Action is not supported.') };
    }

    if (action !== 'scroll' && action !== 'navigate' && (typeof target !== 'string' || !/^element_[1-9]\d*$/.test(target))) {
      return { error: resultError(action, target, 'INVALID_TARGET', 'Target must be a local element identifier.') };
    }

    if (action === 'type' && (typeof input.text !== 'string' || input.text.length === 0)) {
      return { error: resultError(action, target, 'INVALID_TEXT', 'Type action requires non-empty text.') };
    }

    if (action === 'scroll') {
      const direction = input.direction === 'up' ? -1 : input.direction === 'down' ? 1 : 0;
      const amount = Number(input.amount);
      if (!direction || !Number.isFinite(amount) || amount <= 0 || amount > MAX_SCROLL_AMOUNT) {
        return { error: resultError(action, target, 'INVALID_SCROLL', 'Scroll direction or amount is invalid.') };
      }
    }

    if (action === 'navigate') {
      try {
        const url = new URL(input.url);
        if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Unsupported protocol.');
      } catch (error) {
        return { error: resultError(action, target, 'INVALID_URL', 'Navigate requires an HTTP or HTTPS URL.') };
      }
    }

    if (action === 'select' && (typeof input.value !== 'string' || input.value.length === 0)) {
      return { error: resultError(action, target, 'INVALID_OPTION', 'Select action requires an option value.') };
    }

    return { action, target };
  }

  function execute(input) {
    const validation = validateAction(input);
    if (validation.error) return validation.error;

    const { action, target } = validation;
    if (action === 'scroll') {
      const direction = input.direction === 'up' ? -1 : 1;
      window.scrollBy({ top: direction * Number(input.amount), left: 0, behavior: 'smooth' });
      return { success: true, action, target: target || null };
    }

    if (action === 'navigate') {
      window.location.assign(input.url);
      return { success: true, action, target };
    }

    const element = findTarget(target);
    if (!element) return resultError(action, target, 'TARGET_NOT_FOUND', 'The target is not available or visible.');
    if (!isVisible(element)) return resultError(action, target, 'TARGET_NOT_VISIBLE', 'The target is not visible.');
    if (isSensitiveField(element)) {
      return resultError(action, target, 'SENSITIVE_TARGET', 'Interaction with sensitive fields is not allowed.');
    }

    if (action === 'click') {
      element.click();
    } else if (action === 'type') {
      if (!('value' in element)) return resultError(action, target, 'INVALID_TARGET', 'Target is not a text control.');
      element.focus();
      element.value = input.text;
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
    } else if (action === 'select') {
      if (element.tagName.toLowerCase() !== 'select') return resultError(action, target, 'INVALID_TARGET', 'Target is not a select element.');
      if (!Array.from(element.options).some((option) => option.value === input.value)) {
        return resultError(action, target, 'INVALID_OPTION', 'The requested option does not exist.');
      }
      element.value = input.value;
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
    }

    return { success: true, action, target };
  }

  globalThis.actionExecutor = Object.freeze({ execute });
})();
