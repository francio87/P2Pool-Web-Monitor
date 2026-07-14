export function buildDashboardPayload(workers) {
  return {
    data: {
      stratum: { hashrate_15m: 18750, hashrate_1h: 16200, hashrate_24h: 14900, shares_found: 18, shares_failed: 1, current_effort: 37.42, wallet: '44demo' },
      pool: { pool_statistics: { miners: 126, totalBlocksFound: 4102, pplnsWindowSize: 2160, sidechainDifficulty: 184921, sidechainHeight: 381245, hashRate: 278000000 } },
      network: { height: 3478123, difficulty: 452018293827, reward: 0.6123456789 },
      p2p: { uptime_str: '4d 12h', peer_list_size: 18, monero_node: 'node.example:18089', p2pool_version: 'v4.5.1' },
      reliability: { not_enough_data: false, reasons: [], stale_sources: {} },
      workers,
    },
    history: { labels: ['10:00', '10:15', '10:30', '10:45'], hr15m: [12000, 14500, 13200, 18750], hr1h: [11500, 12100, 13500, 16200], shares: [1, 2, 0, 3] },
    meta: { last_update: 'Fixture preview' },
    format: { hashrate_15m: '18.75 KH/s', hashrate_1h: '16.20 KH/s', hashrate_24h: '14.90 KH/s', shares_found: '18', shares_failed: '1', wallet_short: '44demo', sidechain_mode: 'mini', observer_base_url: 'https://mini.p2pool.observer', last_share_ago: '3m ago', pool_hashrate: '278 MH/s', network_reward: '0.612345678900 XMR', p2pool_version_short: '4.5.1', p2pool_latest_version: '4.5.1', p2pool_update_available: false },
  };
}
