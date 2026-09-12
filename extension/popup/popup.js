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
  GET_PAGE_CONTEXT: 'GET_PAGE_CONTEXT'
});

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
  elements.runButton.disabled = true;
  document.body.setAttribute('aria-busy', String(processing));
}

async function requestServiceWorker(type) {
  if (!Object.values(MESSAGE_TYPES).includes(type)) {
    throw new Error('Invalid browser request.');
  }

  const response = await chrome.runtime.sendMessage({ type });
  if (!response || response.ok === false) {
    throw new Error(response?.error?.message || response?.error || 'The browser request failed.');
  }

  return response;
}

async function analyzePage() {
  setProcessing(true);
  setStatus('Analyzing page...');

  try {
    const response = await requestServiceWorker(MESSAGE_TYPES.ANALYZE_PAGE);

    latestAnalysis = response.data || response;
    const elementsFound = latestAnalysis?.elements?.length ?? latestAnalysis?.visualElements?.length;
    const detail = Number.isFinite(elementsFound) ? ` ${elementsFound} elements found.` : '';
    setStatus(`Page analyzed.${detail}`, 'success');
  } catch (error) {
    latestAnalysis = null;
    setStatus(error.message || 'Page analysis failed.', 'error');
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
