/* FraudLab QR Android/touch scroll v8. Only changes iframe scrolling mode.
 * Existing QR scenarios, flow, bridge, timers and sandbox remain unchanged. */
(() => {
  'use strict';
  const frame = document.getElementById('qrSimulationFrame');
  if (!frame) return;
  const touchLayout = window.matchMedia(
    '(max-width: 1366px) and (pointer: coarse), (max-width: 1366px) and (hover: none)'
  );
  const syncScrollMode = () => {
    frame.setAttribute('scrolling', touchLayout.matches ? 'auto' : 'no');
  };
  syncScrollMode();
  if (typeof touchLayout.addEventListener === 'function') {
    touchLayout.addEventListener('change', syncScrollMode);
  } else if (typeof touchLayout.addListener === 'function') {
    touchLayout.addListener(syncScrollMode);
  }
  window.addEventListener('orientationchange', syncScrollMode, { passive: true });
  window.addEventListener('resize', syncScrollMode, { passive: true });
})();
