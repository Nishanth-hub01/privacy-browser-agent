const elements = {
  instruction: document.getElementById('instruction'),
  analyzeButton: document.getElementById('analyze-button'),
  screenshotButton: document.getElementById('screenshot-button'),
  runButton: document.getElementById('run-button'),
  status: document.getElementById('status'),
  statusIndicator: document.getElementById('status-indicator')
};

let latestAnalysis = null;
let latestScreenshot = null;

const MESSAGE_TYPES = Object.freeze({
  ANALYZE_PAGE: 'ANALYZE_PAGE',
  CAPTURE_SCREENSHOT: 'CAPTURE_SCREENSHOT',
  GET_PAGE_CONTEXT: 'GET_PAGE_CONTEXT',
  EXECUTE_ACTION: 'EXECUTE_ACTION'
});

let latestAction = null;

function setStatus(message, state = 'default') {
  elements.status.textContent = message;
  elements.status.className = 'status';
  elements.statusIndicator.className = 'status-indicator';

  if (state === 'success' || state === 'error') {
    elements.status.classList.add(state);
    elements.statusIndicator.classList.add(state);
  }
}

function setProcessing(processing) {
  elements.analyzeButton.disabled = processing;
  elements.screenshotButton.disabled = processing;
  elements.runButton.disabled = processing || !latestAction;
  document.body.setAttribute('aria-busy', String(processing));
}

async function requestServiceWorker(type, payload = {}) {
  if (!Object.values(MESSAGE_TYPES).includes(type)) {
    throw new Error('Invalid browser request.');
  }

  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ type, ...payload }, (response) => {
      const lastError = chrome.runtime.lastError;
      if (lastError) {
        reject(new Error('The extension background worker is not responding. Reload the extension and try again.'));
        return;
      }

      if (!response || response.ok === false) {
        reject(new Error(response?.error?.message || response?.error || 'The browser request failed.'));
        return;
      }

      resolve(response);
    });
  });
}

async function analyzePage() {
  setProcessing(true);
  setStatus('Analyzing page...');

  try {
    const response = await requestServiceWorker(MESSAGE_TYPES.ANALYZE_PAGE, {
      instruction: elements.instruction.value.trim()
    });

    latestAnalysis = response.data || response;
    latestAction = response.action || null;
    const elementsFound = latestAnalysis?.elements?.length ?? latestAnalysis?.visualElements?.length;
    const detail = Number.isFinite(elementsFound) ? ` ${elementsFound} elements found.` : '';
    setStatus(`Workflow complete.${detail}`, 'success');
  } catch (error) {
    latestAnalysis = null;
    latestAction = null;
    setStatus(error.message || 'Page analysis failed.', 'error');
  } finally {
    setProcessing(false);
  }
}

async function runAgent() {
  setProcessing(true);
  setStatus('Running agent...');

  try {
    if (!latestAction) {
      const response = await requestServiceWorker(MESSAGE_TYPES.ANALYZE_PAGE, {
        instruction: elements.instruction.value.trim()
      });
      latestAction = response.action || null;
      latestAnalysis = response.data || response;
      if (!latestAction) {
        throw new Error('The agent did not return a valid action for this page.');
      }
    }

    const response = await requestServiceWorker(MESSAGE_TYPES.EXECUTE_ACTION, { action: latestAction });
    if (!response || response.ok === false) {
      throw new Error(response?.error?.message || 'The agent action was rejected.');
    }

    setStatus('Agent action executed successfully.', 'success');
  } catch (error) {
    setStatus(error.message || 'The agent could not run.', 'error');
  } finally {
    setProcessing(false);
  }
}

async function captureScreenshot() {
  setProcessing(true);
  setStatus('Capturing visible tab...');

  try {
    const response = await requestServiceWorker(MESSAGE_TYPES.CAPTURE_SCREENSHOT);
    latestScreenshot = response.screenshot;

    if (typeof latestScreenshot !== 'string' || latestScreenshot.length === 0) {
      throw new Error('The browser returned an empty screenshot.');
    }

    setStatus('Screenshot captured.', 'success');
  } catch (error) {
    latestScreenshot = null;
    setStatus(error.message || 'Screenshot capture failed.', 'error');
  } finally {
    setProcessing(false);
  }
}

elements.analyzeButton.addEventListener('click', analyzePage);
elements.screenshotButton.addEventListener('click', captureScreenshot);
elements.runButton.addEventListener('click', runAgent);

chrome.runtime.onMessage.addListener((message) => {
  if (message && message.type === 'WORKFLOW_STATUS' && typeof message.message === 'string') {
    setStatus(message.message);
  }
});
