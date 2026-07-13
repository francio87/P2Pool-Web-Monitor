import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { buildDashboardPayload } from './fixtures/dashboard.mjs';
import { DEFAULT_WORKERS, MIXED_WORKER_SCENARIOS, WORKER_SCENARIOS } from './fixtures/workers.mjs';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const templatesDir = path.join(projectRoot, 'src', 'templates');
const port = Number(process.env.PORT || 5174);
const scenarios = {
  default: DEFAULT_WORKERS,
  ...WORKER_SCENARIOS,
  ...MIXED_WORKER_SCENARIOS,
  empty: [],
};

function previewNavigation(activeScenario) {
  const links = [
    ['default', 'All'],
    ['ipv4_lifecycle', 'IPv4'],
    ['ipv6_lifecycle', 'IPv6'],
    ['mixed_15', '15 rigs'],
    ['mixed_30', '30 rigs'],
    ['empty', 'Empty'],
  ];
  return `<nav class="fixture-preview-nav" aria-label="Fixture preview scenarios">
    <strong>Fixture preview</strong>
    ${links.map(([scenario, label]) => `<a href="/${scenario}/"${scenario === activeScenario ? ' aria-current="page"' : ''}>${label}</a>`).join('')}
  </nav>
  <style>
    .fixture-preview-nav { position: fixed; z-index: 100; right: .75rem; bottom: .75rem; display: flex; align-items: center; gap: .3rem; max-width: calc(100vw - 1.5rem); padding: .45rem; border: 1px solid #555; border-radius: .65rem; background: #111e; color: #fff; box-shadow: 0 8px 24px #0008; font: 12px/1.2 system-ui, sans-serif; backdrop-filter: blur(8px); }
    .fixture-preview-nav a { border: 1px solid #555; border-radius: .38rem; padding: .3rem .42rem; color: #fff; text-decoration: none; }
    .fixture-preview-nav a:hover, .fixture-preview-nav a[aria-current="page"] { border-color: #ff7a00; background: #ff7a0026; }
    @media (max-width: 600px) { .fixture-preview-nav { left: .5rem; right: .5rem; bottom: .5rem; flex-wrap: wrap; justify-content: center; } }
  </style>`;
}

function contentType(filePath) {
  if (filePath.endsWith('.html')) return 'text/html';
  if (filePath.endsWith('.css')) return 'text/css';
  if (filePath.endsWith('.js')) return 'text/javascript';
  if (filePath.endsWith('.svg')) return 'image/svg+xml';
  if (filePath.endsWith('.ttf')) return 'font/ttf';
  if (filePath.endsWith('.ico')) return 'image/x-icon';
  return 'application/octet-stream';
}

const server = createServer(async (request, response) => {
  const parts = new URL(request.url, 'http://localhost').pathname.split('/').filter(Boolean);
  const scenario = scenarios[parts[0]] ? parts.shift() : 'default';
  const asset = parts.join('/') || 'p2pool_web_monitor.html';

  if (asset === 'data.json') {
    response.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' });
    response.end(JSON.stringify(buildDashboardPayload(scenarios[scenario])));
    return;
  }

  const filePath = path.resolve(templatesDir, asset);
  if (!filePath.startsWith(`${templatesDir}${path.sep}`)) {
    response.writeHead(403).end();
    return;
  }

  try {
    response.writeHead(200, { 'content-type': contentType(filePath), 'cache-control': 'no-store' });
    if (asset === 'p2pool_web_monitor.html') {
      const html = await readFile(filePath, 'utf8');
      response.end(html.replace('</body>', `${previewNavigation(scenario)}</body>`));
      return;
    }
    response.end(await readFile(filePath));
  } catch {
    response.writeHead(404).end();
  }
});

server.listen(port, '127.0.0.1', () => {
  console.log(`Fixture preview: http://127.0.0.1:${port}/default/`);
  console.log(`Scenarios: ${Object.keys(scenarios).join(', ')}`);
});
