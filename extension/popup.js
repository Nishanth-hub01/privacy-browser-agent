const SERVER_URL = 'http://localhost:8000/api/v1/analyze';
let latestAction = null;

const elements = {
  instruction: document.getElementById('instruction'),
  analyzeBtn: document.getElementById('analyze-btn'),
  executeBtn: document.getElementById('execute-btn'),
  status: document.getElementById('status'),
  actionOutput: document.getElementById('action-output')
};

function setStatus(message, level = 'default') {
  elements.status.textContent = message;
  elements.status.className = 'status';
  if (level === 'success') elements.status.classList.add('success');
  if (level === 'error') elements.status.classList.add('error');
  if (level === 'warning') elements.status.classList.add('warning');
}

function updateOutput(text) {
  elements.actionOutput.textContent = text;
}

function getRequestId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'req-' + Date.now() + '-' + Math.random().toString(16).slice(2);
}

function sanitizeHtml(rawHtml) {
  if (!rawHtml || typeof rawHtml !== 'string') return '';

  let sanitized = rawHtml;
  sanitized = sanitized.replace(/<script[\s\S]*?<\/script>/gi, '<!-- script removed -->');
  sanitized = sanitized.replace(/<style[\s\S]*?<\/style>/gi, '<!-- style removed -->');
  sanitized = sanitized.replace(/value="[^"]*"/gi, 'value="[REDACTED]"');
  sanitized = sanitized.replace(/type="password"/gi, 'type="password" value="[REDACTED]"');
  sanitized = sanitized.replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, '[EMAIL]');
  sanitized = sanitized.replace(/\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b/g, '[PHONE]');
  sanitized = sanitized.replace(/\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g, '[CARD]');
  sanitized = sanitized.replace(/(?<=password\s*[:=]\s*)[^\s<]+/gi, '[PASSWORD]');

  return sanitized.slice(0, 50000);
}

function extractVisualElements(dom) {
  if (!dom || typeof dom !== 'string') return [];

  const parser = new DOMParser();
  const documentFragment = parser.parseFromString(dom, 'text/html');
  const candidates = documentFragment.querySelectorAll('button, a, input, textarea, select, [role="button"], [role="link"], [onclick]');
  const items = [];

  candidates.forEach((element, index) => {
    const label = (element.textContent || element.getAttribute('aria-label') || element.getAttribute('placeholder') || element.getAttribute('value') || '').trim();
    if (!label && !element.id && !element.name) return;

    const item = {
      type: element.tagName.toLowerCase(),
      label: label || undefined,
      id: element.id || undefined,
      selector: element.id ? '#' + CSS.escape(element.id) : undefined,
      x: undefined,
      y: undefined,
      width: undefined,
      height: undefined
    };

    if (items.length < 25) {
      items.push(item);
    }
  });

  return items;
}

async function collectPageContext() {
  const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (!activeTab || !activeTab.id) {
    throw new Error('No active tab found.');
  }

  const pageResponse = await chrome.tabs.sendMessage(activeTab.id, { type: 'collect-page' });
  const screenshot = await chrome.tabs.captureVisibleTab(activeTab.windowId, { format: 'jpeg', quality: 80 });

  return {
    tabId: activeTab.id,
    url: pageResponse?.url || activeTab.url || 'about:blank',
    screenshot,
    dom: pageResponse?.dom || '',
    visualElements: pageResponse?.visualElements || []
  };
}

async function analyzePage() {
  try {
    setStatus('Collecting page context...', 'default');
    const context = await collectPageContext();

    const instruction = (elements.instruction.value || '').trim();
    const payload = {
      request_id: getRequestId(),
      user_instruction: instruction || 'Inspect the page and identify the safest next browser action.',
      sanitized_screenshot: context.screenshot,
      sanitized_dom: sanitizeHtml(context.dom),
      visual_elements: extractVisualElements(context.dom).slice(0, 25)
    };

    setStatus('Sending sanitized context to the server...', 'default');
    updateOutput('Requesting AI action for page: ' + context.url);

    const response = await fetch(SERVER_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    let result;
    try {
      result = await response.json();
    } catch (jsonError) {
      throw new Error('The server responded with invalid JSON.');
    }

    if (!response.ok) {
      throw new Error((result && result.error && result.error.message) || 'Request failed.');
    }

    if (result.status === 'error') {
      throw new Error((result.error && result.error.message) || 'Server returned an error.');
    }

    latestAction = result.action;
    setStatus('Action received and validated.', 'success');
    updateOutput(JSON.stringify(result, null, 2));

    return result;
  } catch (error) {
    const message = error && error.message ? error.message : 'Unknown error while analyzing the page.';
    setStatus(message, 'error');
    updateOutput(error ? String(error) : 'Error');
    return null;
  }
}

async function executeAction(action) {
  const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!activeTab || !activeTab.id) {
    throw new Error('No active tab found.');
  }

  if (!action || !action.type) {
    throw new Error('No valid action to execute.');
  }

  const validAction = validateAction(action);
  if (!validAction) {
    throw new Error('The received action is invalid and was not executed.');
  }

  await chrome.scripting.executeScript({
    target: { tabId: activeTab.id },
    func: function (nextAction) {
      if (!nextAction || !nextAction.type) return;

      if (nextAction.type === 'click') {
        const target = nextAction.target || {};
        const selector = target.id ? '#' + CSS.escape(target.id) : target.selector;
        const element = selector ? document.querySelector(selector) : null;
        if (element) element.click();
      }

      if (nextAction.type === 'scroll') {
        const direction = nextAction.target && nextAction.target.direction === 'up' ? -1 : 1;
        const amount = Math.max(100, Number(nextAction.target && nextAction.target.amount) || 300);
        window.scrollBy({ top: direction * amount, left: 0, behavior: 'smooth' });
      }

      if (nextAction.type === 'type') {
        const target = nextAction.target || {};
        const selector = target.id ? '#' + CSS.escape(target.id) : target.selector;
        const element = selector ? document.querySelector(selector) : null;
        if (element && 'value' in element) {
          element.focus();
          element.value = nextAction.text || '';
          element.dispatchEvent(new Event('input', { bubbles: true }));
          element.dispatchEvent(new Event('change', { bubbles: true }));
        }
      }

      if (nextAction.type === 'navigate') {
        const url = nextAction.target && nextAction.target.url;
        if (url) window.location.href = url;
      }
    },
    args: [validAction]
  });

  setStatus('Action executed successfully.', 'success');
  updateOutput('Executed: ' + JSON.stringify(validAction));
}

function validateAction(action) {
  if (!action || typeof action !== 'object') return null;

  const supported = ['click', 'scroll', 'type', 'navigate'];
  if (!supported.includes(action.type)) return null;

  if (action.type === 'click' || action.type === 'type') {
    const target = action.target || {};
    if (!target || (!target.id && !target.selector && (target.x === undefined || target.y === undefined))) {
      return null;
    }
  }

  if (action.type === 'scroll') {
    const target = action.target || {};
    if (!target || !['up', 'down'].includes(target.direction) || !Number.isFinite(Number(target.amount))) {
      return null;
    }
  }

  if (action.type === 'navigate') {
    const target = action.target || {};
    if (!target || typeof target.url !== 'string' || !target.url.trim()) return null;
  }

  return action;
}

elements.analyzeBtn.addEventListener('click', async () => {
  await analyzePage();
});

elements.executeBtn.addEventListener('click', async () => {
  if (!latestAction) {
    setStatus('No action is available to execute yet.', 'warning');
    return;
  }

  try {
    await executeAction(latestAction);
  } catch (error) {
    setStatus((error && error.message) || 'The action could not be executed.', 'error');
  }
});

window.addEventListener('DOMContentLoaded', () => {
  updateOutput('No action loaded yet.');
});
