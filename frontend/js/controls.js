import { DASHBOARD_THEMES, resolveDashboardTheme } from './theme-presets.js';

const REFRESH_MODES = [
  { key: '30s', seconds: 30, label: '30s' },
  { key: '1m', seconds: 60, label: '1m' },
  { key: '5m', seconds: 300, label: '5m' },
];

export function createDashboardControls({ onRefresh, onThemeChange }) {
  const state = {
    modeKey: localStorage.getItem('p2pool-refresh-mode') || '30s',
    paused: localStorage.getItem('p2pool-refresh-paused') === '1',
    startedAt: 0,
    timerId: null,
    rafId: null,
    progress: 1,
  };

  function getMode() {
    return REFRESH_MODES.find((item) => item.key === state.modeKey) || REFRESH_MODES[0];
  }

  function updateLabel() {
    document.getElementById('refreshRate').textContent = state.paused ? 'Pause' : getMode().label;
  }

  function iconPath(pathData) {
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', pathData);
    return path;
  }

  function updatePauseIcon() {
    const icon = document.getElementById('pauseResumeIcon');
    const button = document.getElementById('pauseResumeBtn');
    if (!icon || !button) return;
    if (state.paused) {
      icon.replaceChildren(iconPath('M8 5l11 7-11 7z'));
      button.setAttribute('aria-label', 'Resume auto refresh');
      button.setAttribute('title', 'Resume auto refresh');
    } else {
      icon.replaceChildren(iconPath('M10 5h2v14h-2z'), iconPath('M14 5h2v14h-2z'));
      button.setAttribute('aria-label', 'Pause auto refresh');
      button.setAttribute('title', 'Pause auto refresh');
    }
  }

  function stopAnimations() {
    if (state.timerId) clearTimeout(state.timerId);
    if (state.rafId) cancelAnimationFrame(state.rafId);
    state.timerId = null;
    state.rafId = null;
  }

  function runProgress() {
    const bar = document.getElementById('refreshProgressBar');
    const totalMs = getMode().seconds * 1000;
    if (!bar || totalMs <= 0) return;
    function tick() {
      const remaining = Math.max(0, 1 - ((Date.now() - state.startedAt) / totalMs));
      state.progress = remaining;
      bar.style.transform = `scaleX(${remaining})`;
      if (remaining > 0) state.rafId = requestAnimationFrame(tick);
    }
    state.rafId = requestAnimationFrame(tick);
  }

  function schedule(resetProgress = true) {
    stopAnimations();
    if (resetProgress) state.progress = 1;
    updateLabel();
    updatePauseIcon();
    const bar = document.getElementById('refreshProgressBar');
    if (state.paused) {
      if (bar) bar.style.transform = `scaleX(${state.progress})`;
      return;
    }
    state.startedAt = Date.now();
    state.progress = 1;
    if (bar) bar.style.transform = 'scaleX(1)';
    runProgress();
    state.timerId = setTimeout(onRefresh, getMode().seconds * 1000);
  }

  function setDashboardTheme(theme) {
    const selectedTheme = resolveDashboardTheme(theme, localStorage.getItem('p2pool-theme'));
    const preset = DASHBOARD_THEMES[selectedTheme];
    document.documentElement.setAttribute('data-dashboard-theme', preset.dashboardTheme);
    document.documentElement.setAttribute('data-theme', preset.colorMode);
    localStorage.setItem('p2pool-dashboard-theme', selectedTheme);
    document.getElementById('dashboardTheme').value = selectedTheme;
  }

  function initialize() {
    const themeMenuToggle = document.getElementById('themeMenuToggle');
    const themePopover = document.getElementById('themePopover');
    const themeMenu = themeMenuToggle.closest('.theme-menu');
    const setThemeMenuOpen = (isOpen) => {
      themePopover.classList.toggle('is-open', isOpen);
      themeMenuToggle.setAttribute('aria-expanded', String(isOpen));
    };

    setDashboardTheme(localStorage.getItem('p2pool-dashboard-theme') || 'classic-dark');
    themeMenuToggle.addEventListener('click', () => {
      setThemeMenuOpen(!themePopover.classList.contains('is-open'));
    });
    document.addEventListener('click', (event) => {
      if (!themeMenu.contains(event.target)) setThemeMenuOpen(false);
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        setThemeMenuOpen(false);
        themeMenuToggle.focus();
      }
    });
    document.getElementById('dashboardTheme').addEventListener('change', (event) => {
      setDashboardTheme(event.target.value);
      setThemeMenuOpen(false);
      onThemeChange();
    });
    document.getElementById('refreshRate').addEventListener('click', () => {
      const index = REFRESH_MODES.findIndex((item) => item.key === state.modeKey);
      state.modeKey = REFRESH_MODES[(index + 1) % REFRESH_MODES.length].key;
      localStorage.setItem('p2pool-refresh-mode', state.modeKey);
      state.paused = false;
      localStorage.setItem('p2pool-refresh-paused', '0');
      schedule();
    });
    document.getElementById('pauseResumeBtn').addEventListener('click', () => {
      state.paused = !state.paused;
      localStorage.setItem('p2pool-refresh-paused', state.paused ? '1' : '0');
      schedule(false);
    });
    document.getElementById('refreshNowBtn').addEventListener('click', onRefresh);
  }

  return { initialize, schedule, updateLabel };
}
