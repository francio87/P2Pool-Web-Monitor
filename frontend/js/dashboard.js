import { createChartRenderer } from './charts.js';
import { createDashboardControls } from './controls.js';
import { createDashboardRenderer } from './renderer.js';

export function initDashboard() {
      const DATA_URL = 'data.json';

      function createEmptyPayload() {
        return {
          data: {
            status: 'Waiting for data',
            stratum: {
              hashrate_15m: 0,
              hashrate_1h: 0,
              hashrate_24h: 0,
              shares_found: 0,
              shares_failed: 0,
              current_effort: 0,
              wallet: '',
            },
            pool: { pool_statistics: { miners: 0, totalBlocksFound: 0, pplnsWindowSize: 0, sidechainDifficulty: 0, sidechainHeight: 0, hashRate: 0 } },
            network: { height: 0, difficulty: 0, reward: 0 },
            p2p: {
              uptime_str: 'Waiting...',
              peer_list_size: 0,
              monero_node: 'Waiting...',
              p2pool_version: '',
              version_check: { enabled: true, latest_version: '', update_available: false },
            },
            peers: { public_count: 0, onion_count: 0 },
            freshness: {},
            reliability: { not_enough_data: true, reasons: ['warming_up'], stale_sources: {} },
            workers: [],
          },
          history: { labels: [], hr15m: [], hr1h: [], shares: [] },
          meta: { last_update: 'Waiting for first snapshot', refresh_seconds: 30 },
          format: {
            hashrate_15m: '0 H/s',
            hashrate_1h: '0 H/s',
            hashrate_24h: '0 H/s',
            shares_found: '0',
            shares_failed: '0',
            wallet_short: 'Wallet',
            sidechain_mode: 'unknown',
            observer_base_url: 'https://p2pool.observer',
            last_share_ago: 'Never',
            pool_hashrate: '0 H/s',
            network_reward: '0.000000000000 XMR',
            freshness_log: 'Waiting...',
            freshness_stratum: 'Waiting...',
            freshness_p2p: 'Waiting...',
            freshness_pool: 'Waiting...',
            freshness_network: 'Waiting...',
            p2pool_version: 'Unknown',
            p2pool_version_short: 'Unknown',
            p2pool_latest_version: 'Unknown',
            p2pool_update_available: false,
          },
        };
      }

      let payload = createEmptyPayload();

      const uiState = {
        bootstrapped: false,
        fetchError: '',
        fetchInFlight: false,
      };

      const controls = createDashboardControls({
        onRefresh: () => fetchAndRenderPayload(),
        onThemeChange: () => renderCharts(payload),
      });
      const renderCharts = createChartRenderer();
      const renderer = createDashboardRenderer({
        renderCharts,
        updateRefreshLabel: () => controls.updateLabel(),
      });

      function renderAll() {
        renderer.render(payload, uiState);
      }

      async function fetchAndRenderPayload() {
        if (uiState.fetchInFlight) {
          return;
        }
        uiState.fetchInFlight = true;
        try {
          const response = await fetch(`${DATA_URL}?t=${Date.now()}`, { cache: 'no-store' });
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          const nextPayload = await response.json();
          payload = nextPayload;
          uiState.bootstrapped = true;
          uiState.fetchError = '';
        } catch (error) {
          const detail = error instanceof Error ? error.message : String(error || 'unknown error');
          uiState.fetchError = detail;
        } finally {
          uiState.fetchInFlight = false;
          renderAll();
          controls.schedule(true);
        }
      }

      controls.initialize();
      renderAll();
      fetchAndRenderPayload();
}
