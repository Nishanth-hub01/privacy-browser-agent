(() => {
  function captureVisibleScreenshot(windowId) {
    return new Promise((resolve, reject) => {
      try {
        chrome.tabs.captureVisibleTab(
          windowId,
          { format: 'png' },
          (dataUrl) => {
            const runtimeError = chrome.runtime.lastError;
            if (runtimeError) {
              reject(new Error(runtimeError.message));
              return;
            }

            if (typeof dataUrl !== 'string' || !dataUrl) {
              reject(new Error('The browser returned an empty screenshot.'));
              return;
            }

            resolve(dataUrl);
          }
        );
      } catch (error) {
        reject(error instanceof Error ? error : new Error('Screenshot capture failed.'));
      }
    });
  }

  globalThis.captureVisibleScreenshot = captureVisibleScreenshot;
})();
