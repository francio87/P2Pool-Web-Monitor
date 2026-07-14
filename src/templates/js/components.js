export function metricItem(label, value, classes = '') {
  return `<div class="stat ${classes}"><span class="label">${label}</span><span class="value">${value}</span></div>`;
}

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;',
  })[character]);
}

export function formatSidechain(mode) {
  const normalized = String(mode || 'unknown').trim().toLowerCase();
  return normalized || 'unknown';
}

export function asNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

export function formatWorkerHashrate(value) {
  const number = asNumber(value);
  if (number <= 0) return '0 H/s';

  const units = ['H/s', 'KH/s', 'MH/s', 'GH/s', 'TH/s'];
  let scaled = number;
  let index = 0;
  while (scaled >= 1000 && index < units.length - 1) {
    scaled /= 1000;
    index += 1;
  }
  return index === 0 ? `${Math.round(scaled)} ${units[index]}` : `${scaled.toFixed(2)} ${units[index]}`;
}

export function formatAgeSeconds(seconds) {
  const number = Math.max(0, Number(seconds || 0));
  if (number < 60) return `${Math.floor(number)}s`;
  if (number < 3600) return `${Math.floor(number / 60)}m`;
  if (number < 86400) return `${Math.floor(number / 3600)}h`;
  return `${Math.floor(number / 86400)}d`;
}

export function humanizeReason(reason) {
  const labels = {
    missing_stratum_api: 'Missing stratum data',
    missing_pool_api: 'Missing pool data',
    missing_network_api: 'Missing network data',
    stale_stratum: 'Stratum data stale',
    stale_pool: 'Pool data stale',
    stale_network: 'Network data stale',
    stale_p2p: 'P2P data stale',
    stale_log: 'Log data stale',
    warming_up: 'Not enough mining samples yet',
    no_active_workers: 'No active workers currently',
    p2pool_update_available: 'P2Pool update available',
  };
  return labels[reason] || reason;
}
