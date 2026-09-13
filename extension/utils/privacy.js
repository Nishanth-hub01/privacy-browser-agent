(() => {
  const REDACTED = '[REDACTED]';
  const MAX_STRING_LENGTH = 160;
  const MAX_DEPTH = 12;

  const SENSITIVE_KEY_PATTERN = /(?:^|[_-])(password|passcode|passwd|secret|token|auth|authorization|cookie|session|localstorage|sessionstorage|credit.?card|card.?number|cvv|cvc|ssn|social.?security|private.?key|api.?key)(?:$|[_-])/i;
  const SENSITIVE_NAME_PATTERN = /(?:password|passcode|passwd|secret|token|auth|cookie|session|credit.?card|card.?number|cvv|cvc|ssn|social.?security|private.?key|api.?key)/i;
  const EMAIL_PATTERN = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi;
  const PHONE_PATTERN = /\b(?:\+?\d[\d .()\-]{7,}\d)\b/g;
  const BEARER_PATTERN = /\bBearer\s+[A-Za-z0-9._~+\-/]+=*/gi;
  const JWT_PATTERN = /\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g;

  const SAFE_KEYS = new Set([
    'id',
    'type',
    'role',
    'visible',
    'rect',
    'position',
    'x',
    'y',
    'width',
    'height',
    'text',
    'visibleText',
    'ariaLabel',
    'placeholder',
    'name',
    'domId',
    'inputType',
    'title',
    'page',
    'elements'
  ]);

  function isSensitiveKey(key) {
    const normalizedKey = String(key);
    return normalizedKey === 'value' || SENSITIVE_KEY_PATTERN.test(normalizedKey);
  }

  function redactSensitiveText(value) {
    return value
      .replace(BEARER_PATTERN, REDACTED)
      .replace(JWT_PATTERN, REDACTED)
      .replace(EMAIL_PATTERN, REDACTED)
      .replace(PHONE_PATTERN, REDACTED);
  }

  function sanitizeString(value, key) {
    if (isSensitiveKey(key)) return REDACTED;

    const text = redactSensitiveText(String(value));
    const compact = text.replace(/\s+/g, ' ').trim();
    return compact.length > MAX_STRING_LENGTH
      ? `${compact.slice(0, MAX_STRING_LENGTH - 1)}...`
      : compact;
  }

  function sanitizeUrl(value) {
    try {
      const url = new URL(value);
      return `${url.origin}${url.pathname}`;
    } catch (error) {
      return REDACTED;
    }
  }

  function sanitizeValue(value, key = '', depth = 0) {
    if (isSensitiveKey(key)) return REDACTED;
    if (depth > MAX_DEPTH) return REDACTED;
    if (value === null || typeof value === 'boolean' || typeof value === 'number') return value;
    if (typeof value === 'string') {
      return key === 'url' ? sanitizeUrl(value) : sanitizeString(value, key);
    }
    if (Array.isArray(value)) {
      return value.map((item) => sanitizeValue(item, key, depth + 1));
    }
    if (typeof value !== 'object') return REDACTED;

    const sanitized = {};
    Object.keys(value).sort().forEach((childKey) => {
      if (isSensitiveKey(childKey)) {
        sanitized[childKey] = REDACTED;
        return;
      }

      if (SAFE_KEYS.has(childKey) || !SENSITIVE_NAME_PATTERN.test(childKey)) {
        sanitized[childKey] = sanitizeValue(value[childKey], childKey, depth + 1);
      }
    });

    return sanitized;
  }

  function sanitize(value) {
    return sanitizeValue(value);
  }

  globalThis.privacySanitizer = Object.freeze({
    REDACTED,
    sanitize
  });
})();
