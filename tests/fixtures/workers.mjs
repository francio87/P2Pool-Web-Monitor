function worker(name, address, status, hashrateCurrent, lastSeenAgoSeconds = 0) {
  return {
    name,
    remote_address: address,
    status,
    hashrate_data_fresh: status === 'online',
    hashrate_current: hashrateCurrent,
    last_seen_ago_seconds: lastSeenAgoSeconds,
  };
}

export const WORKER_SCENARIOS = Object.freeze({
  ipv4_lifecycle: Object.freeze([
    worker('rig-online', '192.168.1.10', 'online', 12500),
    worker('rig-recently-offline', '192.168.1.11', 'recently_offline', 0, 5),
    worker('rig-offline', '192.168.1.12', 'offline', 0, 900),
  ]),
  ipv6_lifecycle: Object.freeze([
    worker('rig-ipv6-online', '2001:0db8:85a3:0000:0000:8a2e:0370:7334', 'online', 6250),
    worker('rig-ipv6-recently-offline', '2001:0db8:85a3:0000:0000:8a2e:0370:7335', 'recently_offline', 0, 5),
    worker('rig-ipv6-offline', '2001:0db8:85a3:0000:0000:8a2e:0370:7336', 'offline', 0, 900),
  ]),
});

function createMixedWorkers(count) {
  const states = ['online', 'recently_offline', 'offline'];
  return Object.freeze(Array.from({ length: count }, (_, index) => {
    const status = states[index % states.length];
    const isIpv6 = index % 2 === 1;
    const name = index % 7 === 0
      ? `rig-${index + 1}-with-an-intentionally-long-name-for-layout-testing`
      : `rig-${String(index + 1).padStart(2, '0')}`;
    const address = isIpv6
      ? `2001:db8:85a3::${(index + 10).toString(16)}`
      : `192.168.1.${index + 20}`;
    return worker(name, address, status, status === 'online' ? (index + 1) * 1234 : 0, status === 'online' ? 0 : (index + 1) * 60);
  }));
}

export const MIXED_WORKER_SCENARIOS = Object.freeze({
  mixed_15: createMixedWorkers(15),
  mixed_30: createMixedWorkers(30),
});

export const DEFAULT_WORKERS = Object.freeze([
  ...WORKER_SCENARIOS.ipv4_lifecycle,
  ...WORKER_SCENARIOS.ipv6_lifecycle,
]);
