import {
  asNumber,
  formatAgeSeconds,
  formatSidechain,
  formatWorkerHashrate,
  humanizeReason,
} from './components.js';

function element(tagName, className = '', text = null) {
  const node = document.createElement(tagName);
  if (className) node.className = className;
  if (text !== null) node.textContent = String(text);
  return node;
}

function appendContent(parent, content) {
  parent.append(content instanceof Node ? content : document.createTextNode(String(content)));
}

function metricItem(label, value, classes = '') {
  const card = element('div', `stat ${classes}`.trim());
  const labelNode = element('span', 'label');
  const valueNode = element('span', 'value');
  appendContent(labelNode, label);
  appendContent(valueNode, value);
  card.append(labelNode, valueNode);
  return card;
}

function stackedValue(stackClass, rowClass, tagClass, valueClass, rows) {
  const stack = element('span', stackClass);
  for (const [tag, value, extraClass = ''] of rows) {
    const row = element('span', rowClass);
    row.append(element('span', tagClass, tag), element('span', `${valueClass} ${extraClass}`.trim(), value));
    stack.append(row);
  }
  return stack;
}

function replaceContent(container, nodes) {
  container.replaceChildren(...nodes);
}

export function createDashboardRenderer({ renderCharts, updateRefreshLabel }) {
  function updateLastUpdateLabel(payload) {
    const el = document.getElementById('lastUpdate');
    if (el) el.textContent = payload.meta?.last_update || 'Waiting for first snapshot';
  }

  function setBanner(banner, label, message) {
    banner.replaceChildren(element('strong', '', label), document.createTextNode(` ${message}`));
    banner.style.display = 'block';
  }

  function renderReliability(payload, uiState) {
    const reliability = payload.data?.reliability || {};
    const reasons = reliability.reasons || [];
    const stale = reliability.stale_sources || {};
    const banner = document.getElementById('reliabilityBanner');
    const badge = document.getElementById('statusBadge');
    const warning = (status, label, message) => {
      badge.textContent = status;
      badge.classList.remove('badge-online');
      badge.classList.add('badge-warning');
      setBanner(banner, label, message);
    };
    const reasonsText = reasons.map(humanizeReason).join(' · ') || 'Data sources not ready';

    if (!uiState.bootstrapped && uiState.fetchError) {
      warning('Waiting', 'Waiting for first monitor snapshot:', uiState.fetchError);
    } else if (uiState.bootstrapped && uiState.fetchError) {
      warning('Update Error', 'Live update failed:', uiState.fetchError);
    } else if (payload.format?.p2pool_update_available) {
      warning('Update Available', 'P2Pool update available:', `installed ${payload.format?.p2pool_version_short || 'unknown'}, latest ${payload.format?.p2pool_latest_version || 'unknown'}`);
    } else if (reliability.not_enough_data) {
      warning('Limited Data', 'Warm-up in progress:', reasonsText);
    } else if (Object.values(stale).some(Boolean)) {
      warning('Stale Sources', 'Data warning:', reasonsText);
    } else {
      badge.textContent = 'Online';
      badge.classList.add('badge-online');
      badge.classList.remove('badge-warning');
      banner.style.display = 'none';
      banner.replaceChildren();
    }
  }

  function renderStats(payload) {
    const s = payload.data?.stratum || {};
    const p = payload.data?.pool?.pool_statistics || {};
    const n = payload.data?.network || {};
    const p2p = payload.data?.p2p || {};
    const workers = payload.data?.workers || [];
    const workersOnline = workers.filter((worker) => worker.status === 'online').length;
    const failedShares = asNumber(s.shares_failed);
    const failedClass = failedShares > 0 ? 'danger' : '';
    const version = String(payload.format?.p2pool_version_short || '').replace(/^v/i, '').trim();
    const latestVersion = String(payload.format?.p2pool_latest_version || '').replace(/^v/i, '').trim();
    const updateAvailable = Boolean(payload.format?.p2pool_update_available);

    const walletChip = document.getElementById('walletChip');
    const walletRaw = String(s.wallet || '').trim();
    const observerBaseUrl = String(payload.format?.observer_base_url || 'https://p2pool.observer').replace(/\/$/, '');
    document.getElementById('walletChipText').textContent = payload.format?.wallet_short || 'Wallet';
    walletChip.href = walletRaw ? `${observerBaseUrl}/miner/${encodeURIComponent(walletRaw)}` : `${observerBaseUrl}/`;
    updateRefreshLabel();
    updateLastUpdateLabel(payload);

    const nodeLabel = element('span', 'label-with-badge');
    nodeLabel.append(element('span', '', 'Node'));
    if (version && version !== 'Unknown') {
      const badge = element('span', updateAvailable ? 'label-badge update-available' : 'label-badge', `P2Pool v${version}`);
      badge.title = updateAvailable
        ? `New P2Pool version available: v${latestVersion || 'unknown'} (installed v${version})`
        : `Installed P2Pool version: v${version}`;
      nodeLabel.append(badge);
    }

    replaceContent(document.getElementById('myStratum'), [
      metricItem('Hashrate', stackedValue('hashrate-triplet', 'hashrate-row', 'hashrate-tag', 'hashrate-value', [
        ['15M', payload.format?.hashrate_15m || '0 H/s'], ['1H', payload.format?.hashrate_1h || '0 H/s'], ['24H', payload.format?.hashrate_24h || '0 H/s'],
      ]), 'primary hashrate-compact'),
      metricItem('Workers Online', `${workersOnline}/${workers.length}`, workersOnline === 0 ? 'danger' : ''),
      metricItem('Shares', stackedValue('shares-triplet', 'shares-row', 'shares-tag', 'shares-value', [
        ['FOUND', payload.format?.shares_found || '0'], ['FAILED', payload.format?.shares_failed || '0', failedClass], ['LAST', payload.format?.last_share_ago || 'Never'],
      ]), `shares-compact ${failedClass}`.trim()),
      metricItem(nodeLabel, stackedValue('node-stack', 'node-row', 'node-tag', 'node-value', [
        ['UPTIME', p2p.uptime_str || 'Waiting...'], ['NODE', p2p.monero_node || 'Waiting...'], ['CHAIN', formatSidechain(payload.format?.sidechain_mode)],
      ])),
    ]);

    replaceContent(document.getElementById('workerContext'), [
      metricItem('Current Effort', `${asNumber(s.current_effort).toFixed(2)}%`, 'primary'),
      element('div', 'context-separator'),
      metricItem('Global Hashrate', payload.format?.pool_hashrate || '0 H/s'),
      metricItem('Total Miners', p.miners ?? 0),
    ]);

    replaceContent(document.getElementById('poolStats'), [
      metricItem('Version', payload.format?.p2pool_version_short || 'Unknown'), metricItem('Chain', formatSidechain(payload.format?.sidechain_mode)),
      metricItem('Sidechain Height', p.sidechainHeight ?? 0), metricItem('Sidechain Diff', p.sidechainDifficulty ?? 0),
      metricItem('PPLNS Window', p.pplnsWindowSize ?? 0), metricItem('Blocks Found', p.totalBlocksFound ?? 0),
    ]);

    replaceContent(document.getElementById('networkStats'), [
      metricItem('Network Height', n.height ?? 0), metricItem('Difficulty', n.difficulty ?? 0),
      metricItem('Reward', payload.format?.network_reward || '0.000000000000 XMR', 'primary'), metricItem('P2P Peers', p2p.peer_list_size ?? 0),
    ]);
  }

  function renderWorkers(payload) {
    const workers = payload.data?.workers || [];
    const tbody = document.getElementById('workersTable');
    const online = workers.filter((worker) => worker.status === 'online').length;
    document.getElementById('workerCount').textContent = `${online} active`;

    if (!workers.length) {
      const cell = element('td', 'muted', 'Waiting for worker data');
      cell.colSpan = 5;
      tbody.replaceChildren(element('tr', '', null));
      tbody.firstChild.append(cell);
      return;
    }

    const fragment = document.createDocumentFragment();
    for (const worker of workers) {
      const statusMap = {
        recently_offline: ['recently-offline', 'Recently offline'],
        offline: ['offline', 'Offline'],
      };
      const [status, statusText] = statusMap[worker.status] || ['online', 'Online'];
      const hashrate = status === 'online'
        ? (worker.hashrate_data_fresh ? formatWorkerHashrate(worker.hashrate_current || 0) : 'Not enough data')
        : '0 H/s';
      const lastSeen = status === 'online' ? 'now' : `${formatAgeSeconds(worker.last_seen_ago_seconds || 0)} ago`;
      const row = element('tr', status);
      row.append(
        element('td', '', worker.name || worker.id || 'Worker'),
        element('td', '', worker.remote_address || 'N/A'),
        element('td', '', hashrate),
      );
      const statusCell = element('td');
      statusCell.append(element('span', `worker-status ${status}`, statusText));
      row.append(statusCell, element('td', '', lastSeen));
      fragment.append(row);
    }
    tbody.replaceChildren(fragment);
  }

  return {
    render(payload, uiState) {
      renderStats(payload);
      renderReliability(payload, uiState);
      renderWorkers(payload);
      renderCharts(payload);
    },
  };
}
