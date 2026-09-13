(() => {
  const MAX_TEXT_LENGTH = 160;
  const TARGET_PATTERNS = [
    { pattern: /log\s*in|sign\s*in|submit|continue|next/i, intent: 'identify primary action', confidence: 0.95 },
    { pattern: /search|find/i, intent: 'identify search control', confidence: 0.92 },
    { pattern: /cancel|close|back/i, intent: 'identify navigation control', confidence: 0.9 }
  ];

  function compactText(value) {
    const text = String(value || '').replace(/\s+/g, ' ').trim();
    return text.length > MAX_TEXT_LENGTH
      ? `${text.slice(0, MAX_TEXT_LENGTH - 1)}...`
      : text;
  }

  function getDomElements(dom) {
    if (!dom || typeof dom !== 'object' || !Array.isArray(dom.elements)) return [];
    return dom.elements.filter((element) => (
      element &&
      typeof element === 'object' &&
      typeof element.id === 'string' &&
      typeof element.type === 'string'
    ));
  }

  function getElementText(element) {
    return compactText([
      element.text,
      element.ariaLabel,
      element.placeholder,
      element.role,
      element.name
    ].filter(Boolean).join(' '));
  }

  function findTarget(elements) {
    const visibleElements = elements.filter((element) => element.visible !== false);

    for (const candidate of TARGET_PATTERNS) {
      const match = visibleElements.find((element) => candidate.pattern.test(getElementText(element)));
      if (match) {
        return {
          intent: candidate.intent,
          target: {
            type: match.type,
            identifier: match.id
          },
          confidence: candidate.confidence
        };
      }
    }

    const button = visibleElements.find((element) => (
      element.type === 'button' || element.role === 'button' || element.inputType === 'submit'
    ));
    if (button) {
      return {
        intent: 'identify available button',
        target: {
          type: button.type,
          identifier: button.id
        },
        confidence: 0.75
      };
    }

    const control = visibleElements.find((element) => (
      ['input', 'textarea', 'select'].includes(element.type)
    ));
    if (control) {
      return {
        intent: 'identify available form control',
        target: {
          type: control.type,
          identifier: control.id
        },
        confidence: 0.65
      };
    }

    return {
      intent: 'no actionable element identified',
      target: null,
      confidence: 0
    };
  }

  function normalizeDom(dom) {
    if (globalThis.privacySanitizer && typeof globalThis.privacySanitizer.sanitize === 'function') {
      return globalThis.privacySanitizer.sanitize(dom);
    }

    return dom && typeof dom === 'object' ? dom : {};
  }

  function perceive(input = {}) {
    const dom = normalizeDom(input.dom);
    const elements = getDomElements(dom);
    const perception = findTarget(elements);

    // Replace this deterministic mock with a local model adapter later.
    // The adapter should receive sanitized DOM metadata and local visual features,
    // then return the same intent/target/confidence contract.
    return {
      intent: perception.intent,
      target: perception.target,
      confidence: perception.confidence,
      sources: {
        dom: elements.length > 0,
        screenshot: typeof input.screenshot === 'string' && input.screenshot.length > 0
      }
    };
  }

  globalThis.localAi = Object.freeze({ perceive });
})();
