import { initDashboard } from './js/dashboard.js';

function startDashboard() {
  try {
    initDashboard();
  } catch (error) {
    console.error('Dashboard initialization failed', error);
    const banner = document.getElementById('reliabilityBanner');
    if (banner) {
      banner.textContent = `Dashboard initialization failed: ${error instanceof Error ? error.message : String(error)}`;
      banner.style.display = 'block';
    }
  }
}

if (document.readyState === 'complete') {
  startDashboard();
} else {
  window.addEventListener('load', startDashboard, { once: true });
}
