(() => {
  'use strict';

  let lastHeight = 0;
  let lastActivityPost = 0;

  const post = (type, extra = {}) => {
    if (window.parent !== window) {
      window.parent.postMessage({ type, ...extra }, '*');
    }
  };

  const reportActivity = () => {
    const now = Date.now();
    if (now - lastActivityPost < 500) {
      return;
    }
    lastActivityPost = now;
    post('fraudlab:simulation-activity');
  };

  const reportHeight = () => {
    window.requestAnimationFrame(() => {
      const height = Math.ceil(Math.max(
        document.documentElement.scrollHeight,
        document.body ? document.body.scrollHeight : 0,
        document.documentElement.offsetHeight,
        document.body ? document.body.offsetHeight : 0
      ));

      if (height > 0 && height !== lastHeight) {
        lastHeight = height;
        post('fraudlab:qr-sim-height', { height });
      }
    });
  };

  const scrollTop = () => {
    post('fraudlab:qr-sim-scroll-top');
    lastHeight = 0;
    reportHeight();
  };

  window.FraudLabQRSim = { reportHeight, scrollTop };

  if ('ResizeObserver' in window && document.body) {
    new ResizeObserver(() => {
      lastHeight = 0;
      reportHeight();
    }).observe(document.body);
  }

  if ('MutationObserver' in window && document.body) {
    new MutationObserver(() => {
      lastHeight = 0;
      reportHeight();
    }).observe(document.body, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ['class', 'style', 'hidden']
    });
  }

  window.addEventListener('load', reportHeight, { once: true });
  window.addEventListener('resize', () => {
    lastHeight = 0;
    reportHeight();
  });
  ['pointerdown', 'touchstart', 'wheel', 'keydown', 'input'].forEach(eventName => {
    document.addEventListener(eventName, reportActivity, { passive: true });
  });

  document.addEventListener('input', () => {
    lastHeight = 0;
    reportHeight();
  }, { passive: true });
  document.addEventListener('click', () => {
    reportActivity();
    window.setTimeout(() => {
      lastHeight = 0;
      reportHeight();
    }, 0);
  }, { passive: true });

  reportHeight();
})();
