(() => {
  const DEFAULT_BACKEND_URL = 'http://localhost:8000';
  const REQUEST_TIMEOUT_MS = 10000;
  const REDACTED = '[REDACTED]';
  let configuredBackendUrl = '';

  const SENSITIVE_KEY_PATTERN = /(?:password|passcode|passwd|secret|token|auth|authorization|cookie|session|localstorage|sessionstorage|credit.?card|card.?number|cvv|cvc|ssn|private.?key|api.?key|value)/i;
  const EMAIL_PATTERN = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi;
  const BEARER_PATTERN = /\bBearer\s+[A-Za-z0-9._~+\-/]+=*/gi;
  const JWT_PATTERN = /\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g;

  function getBackendUrl() {
    const runtimeUrl = globalThis.browserAgentConfig && globalThis.browserAgentConfig.backendUrl;
    return String(configuredBackendUrl || runtimeUrl || DEFAULT_BACKEND_URL).replace(/\/+$/, '');
  }

  function configure(options = {}) {
    if (typeof options.backendUrl !== 'string' || !options.backendUrl.trim()) {
      throw new Error('A non-empty backend URL is required.');
    }

    const url = new URL(options.backendUrl);
    if (!['http:', 'https:'].includes(url.protocol)) {
      throw new Error('Backend URL must use HTTP or HTTPS.');
    }

    configuredBackendUrl = url.toString().replace(/\/+$/, '');
  }

  function sanitizeString(value) {
    return String(value)
      .replace(BEARER_PATTERN, REDACTED)
      .replace(JWT_PATTERN, REDACTED)
      .replace(EMAIL_PATTERN, REDACTED)
      .replace(/\s+/g, ' ')
      .trim();
  }

  function sanitizeValue(value, key = '', depth = 0) {
    if (SENSITIVE_KEY_PATTERN.test(String(key))) return REDACTED;
    if (depth > 10) return REDACTED;
    if (value === null || typeof value === 'boolean' || typeof value === 'number') return value;
    if (typeof value === 'string') return sanitizeString(value);
    if (Array.isArray(value)) return value.map((item) => sanitizeValue(item, key, depth + 1));
    if (typeof value !== 'object') return REDACTED;

    const result = {};
    Object.keys(value).sort().forEach((childKey) => {
      result[childKey] = sanitizeValue(value[childKey], childKey, depth + 1);
    });
    return result;
  }

  function sanitizeContext(context) {
    if (!context || typeof context !== 'object' || Array.isArray(context)) {
      throw new Error('Context must be a JSON object.');
    }

    const sanitized = {
      screenshot: typeof context.screenshot === 'string' ? context.screenshot : null,
      dom: null,
      user_instruction: typeof context.user_instruction === 'string'
        ? sanitizeString(context.user_instruction)
        : undefined
    };

    if (context.dom && typeof context.dom === 'object' && !Array.isArray(context.dom)) {
      sanitized.dom = globalThis.privacySanitizer && typeof globalThis.privacySanitizer.sanitize === 'function'
        ? globalThis.privacySanitizer.sanitize(context.dom)
        : sanitizeValue(context.dom, 'dom');
    } else if (context.dom !== undefined && context.dom !== null) {
      throw new Error('DOM context must be structured sanitized metadata, not raw HTML.');
    }

    return sanitized;
  }

  async function request(path, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(`${getBackendUrl()}${path}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {})
        },
        signal: controller.signal
      });

      let body = null;
      try {
        body = await response.json();
      } catch (error) {
        if (!response.ok) throw new Error(`Backend returned HTTP ${response.status}.`);
        throw new Error('Backend returned invalid JSON.');
      }

      if (!response.ok) {
        const detail = body && (body.detail || body.error || body.message);
        throw new Error(`Backend returned HTTP ${response.status}: ${detail || 'request failed.'}`);
      }

      return body;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('Backend request timed out.');
      if (error instanceof TypeError) throw new Error('Backend network request failed.');
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  async function sendContextToBackend(context) {
    const sanitizedContext = sanitizeContext(context);
    return request('/api/v1/analyze', {
      method: 'POST',
      body: JSON.stringify(sanitizedContext)
    });
  }

  async function healthCheck() {
    return request('/health', { method: 'GET' });
  }

  globalThis.browserAgentApi = Object.freeze({
    configure,
    sendContextToBackend,
    healthCheck
  });
})();
