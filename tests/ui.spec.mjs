import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';
import { DASHBOARD_THEMES } from '../frontend/js/theme-presets.js';
import { buildDashboardPayload } from './fixtures/dashboard.mjs';
import { DEFAULT_WORKERS, MIXED_WORKER_SCENARIOS, WORKER_SCENARIOS } from './fixtures/workers.mjs';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const templatesDir = path.join(projectRoot, 'src', 'templates');
const fixture = buildDashboardPayload(DEFAULT_WORKERS);

let server;
let baseUrl;

function contentType(filePath) {
  if (filePath.endsWith('.html')) return 'text/html';
  if (filePath.endsWith('.css')) return 'text/css';
  if (filePath.endsWith('.js')) return 'text/javascript';
  if (filePath.endsWith('.svg')) return 'image/svg+xml';
  if (filePath.endsWith('.json')) return 'application/json';
  return 'application/octet-stream';
}

test.beforeAll(async () => {
  server = createServer(async (request, response) => {
    const pathname = new URL(request.url, 'http://localhost').pathname;
    if (pathname === '/data.json') {
      response.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' });
      response.end(JSON.stringify(fixture));
      return;
    }

    const relativePath = pathname === '/' ? 'p2pool_web_monitor.html' : pathname.slice(1);
    const filePath = path.resolve(templatesDir, relativePath);
    if (!filePath.startsWith(`${templatesDir}${path.sep}`)) {
      response.writeHead(403).end();
      return;
    }

    try {
      response.writeHead(200, { 'content-type': contentType(filePath), 'cache-control': 'no-store' });
      response.end(await readFile(filePath));
    } catch {
      response.writeHead(404).end();
    }
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

test.afterAll(async () => new Promise((resolve) => server.close(resolve)));

test('theme popover selects and persists a complete theme preset', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: 'networkidle' });

  await page.locator('#themeMenuToggle').click();
  await expect(page.locator('#themePopover')).toBeVisible();
  await page.locator('#dashboardTheme').selectOption('market-dark');
  await expect(page.locator('html')).toHaveAttribute('data-dashboard-theme', 'market-dark');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await expect(page.locator('#themePopover')).toBeHidden();

  await page.reload({ waitUntil: 'networkidle' });
  await expect(page.locator('#dashboardTheme')).toHaveValue('market-dark');
  expect(await page.evaluate(() => localStorage.getItem('p2pool-dashboard-theme'))).toBe('market-dark');
  expect(pageErrors).toEqual([]);
});

test('classic light preset and refresh controls are interactive', async ({ page }) => {
  await page.goto(baseUrl, { waitUntil: 'networkidle' });

  await page.locator('#themeMenuToggle').click();
  await page.locator('#dashboardTheme').selectOption('classic-light');
  await expect(page.locator('html')).toHaveAttribute('data-dashboard-theme', 'classic');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');

  const refreshRate = page.locator('#refreshRate');
  await expect(refreshRate).toHaveText('30s');
  await refreshRate.click();
  await expect(refreshRate).toHaveText('1m');

  const pauseButton = page.locator('#pauseResumeBtn');
  await pauseButton.click();
  await expect(pauseButton).toHaveAttribute('aria-label', 'Resume auto refresh');
  await pauseButton.click();
  await expect(pauseButton).toHaveAttribute('aria-label', 'Pause auto refresh');
});

const RELIABILITY_BANNER_SCENARIOS = [
  {
    name: 'reports an available P2Pool update',
    configure(payload) {
      payload.format.p2pool_update_available = true;
      payload.format.p2pool_version_short = '4.5.1';
      payload.format.p2pool_latest_version = '4.6.0';
    },
    status: 'Update Available',
    text: 'P2Pool update available: installed 4.5.1, latest 4.6.0',
  },
  {
    name: 'prioritizes an update over simultaneous warm-up and stale-source warnings',
    configure(payload) {
      payload.format.p2pool_update_available = true;
      payload.format.p2pool_version_short = '4.5.1';
      payload.format.p2pool_latest_version = '4.6.0';
      payload.data.reliability = {
        not_enough_data: true,
        reasons: ['warming_up', 'stale_stratum'],
        stale_sources: { stratum: true },
      };
    },
    status: 'Update Available',
    text: 'P2Pool update available: installed 4.5.1, latest 4.6.0',
  },
  {
    name: 'reports monitor warm-up',
    configure(payload) {
      payload.data.reliability = { not_enough_data: true, reasons: ['warming_up'], stale_sources: {} };
    },
    status: 'Limited Data',
    text: 'Warm-up in progress: Not enough mining samples yet',
  },
  {
    name: 'reports stale sources',
    configure(payload) {
      payload.data.reliability = { not_enough_data: false, reasons: ['stale_stratum'], stale_sources: { stratum: true } };
    },
    status: 'Stale Sources',
    text: 'Data warning: Stratum data stale',
  },
];

for (const scenario of RELIABILITY_BANNER_SCENARIOS) {
  test(`reliability banner ${scenario.name}`, async ({ page }) => {
    const payload = structuredClone(fixture);
    scenario.configure(payload);
    await page.route('**/data.json**', (route) => route.fulfill({ json: payload }));
    await page.goto(baseUrl, { waitUntil: 'networkidle' });

    const banner = page.locator('#reliabilityBanner');
    await expect(banner).toBeVisible();
    await expect(banner).toHaveText(scenario.text);
    await expect(page.locator('#statusBadge')).toHaveText(scenario.status);
    await expect(page.locator('#statusBadge')).toHaveClass(/badge-warning/);

    await page.setViewportSize({ width: 390, height: 844 });
    for (const preset of Object.keys(DASHBOARD_THEMES)) {
      await page.locator('#themeMenuToggle').click();
      await page.locator('#dashboardTheme').selectOption(preset);
      expect(await banner.evaluate((element) => element.scrollWidth <= element.clientWidth + 1), `${scenario.name}/${preset} banner overflow`).toBe(true);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `${scenario.name}/${preset} document overflow`).toBe(true);
    }
  });
}

test('reliability banner reports a failed first monitor snapshot', async ({ page }) => {
  await page.route('**/data.json**', (route) => route.fulfill({ status: 503, body: 'Monitor unavailable' }));
  await page.goto(baseUrl, { waitUntil: 'networkidle' });

  await expect(page.locator('#reliabilityBanner')).toHaveText('Waiting for first monitor snapshot: HTTP 503');
  await expect(page.locator('#statusBadge')).toHaveText('Waiting');
  await expect(page.locator('#statusBadge')).toHaveClass(/badge-warning/);
});

test('a failed refresh takes precedence over an update notification', async ({ page }) => {
  const payload = structuredClone(fixture);
  payload.format.p2pool_update_available = true;
  payload.format.p2pool_latest_version = '4.6.0';
  let requests = 0;
  await page.route('**/data.json**', (route) => {
    requests += 1;
    if (requests === 1) {
      return route.fulfill({ json: payload });
    }
    return route.fulfill({ status: 503, body: 'Monitor unavailable' });
  });
  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  await expect(page.locator('#statusBadge')).toHaveText('Update Available');

  const failedRefresh = page.waitForResponse((response) => response.url().includes('/data.json') && response.status() === 503);
  await page.locator('#refreshNowBtn').click();
  await failedRefresh;

  await expect(page.locator('#reliabilityBanner')).toHaveText('Live update failed: HTTP 503');
  await expect(page.locator('#statusBadge')).toHaveText('Update Error');
  await expect(page.locator('#statusBadge')).toHaveClass(/badge-warning/);
});

test('empty worker data renders a safe placeholder', async ({ page }) => {
  const originalWorkers = fixture.data.workers;
  fixture.data.workers = [];
  try {
    await page.goto(baseUrl, { waitUntil: 'networkidle' });
    await expect(page.locator('#workersTable')).toContainText('Waiting for worker data');
    await expect(page.locator('#workerCount')).toHaveText('0 active');
  } finally {
    fixture.data.workers = originalWorkers;
  }
});

test('mobile header keeps the palette control reachable without page overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(baseUrl, { waitUntil: 'networkidle' });

  await expect(page.locator('#themeMenuToggle')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.locator('#themeMenuToggle').click();
  await expect(page.locator('#themePopover')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('#themePopover')).toBeHidden();
});

async function expectNoHeaderOrWorkerTableOverlap(page) {
  const overlaps = await page.evaluate(() => {
    const intersects = (first, second) => (
      first.left < second.right - 1
      && first.right > second.left + 1
      && first.top < second.bottom - 1
      && first.bottom > second.top + 1
    );
    const visible = (element) => {
      const style = getComputedStyle(element);
      return style.display !== 'none' && style.visibility !== 'hidden';
    };
    const issues = [];
    const headerItems = [...document.querySelectorAll('.header-left, .header-controls')]
      .filter(visible)
      .map((element) => ({ name: element.className, box: element.getBoundingClientRect() }));
    for (let index = 0; index < headerItems.length; index += 1) {
      for (let next = index + 1; next < headerItems.length; next += 1) {
        if (intersects(headerItems[index].box, headerItems[next].box)) {
          issues.push(`header:${headerItems[index].name}/${headerItems[next].name}`);
        }
      }
    }
    for (const row of document.querySelectorAll('.workers-table tr')) {
      const cells = [...row.children].filter(visible).map((cell) => ({ element: cell, text: cell.textContent.trim(), box: cell.getBoundingClientRect() }));
      for (const cell of cells) {
        if (cell.element.scrollWidth > cell.element.clientWidth + 1) {
          issues.push(`worker-cell:overflow:${cell.text}`);
        }
      }
      const statusBadge = row.querySelector('.worker-status');
      const statusCell = statusBadge?.closest('td');
      const lastSeenCell = row.children[4];
      if (statusBadge && statusCell && visible(lastSeenCell)) {
        const badgeBox = statusBadge.getBoundingClientRect();
        if (badgeBox.right > statusCell.getBoundingClientRect().right + 1 || intersects(badgeBox, lastSeenCell.getBoundingClientRect())) {
          issues.push(`worker-status:overlap:${statusBadge.textContent.trim()}`);
        }
      }
      for (let index = 0; index < cells.length; index += 1) {
        for (let next = index + 1; next < cells.length; next += 1) {
          if (intersects(cells[index].box, cells[next].box)) {
            issues.push(`worker-row:${cells[index].text}/${cells[next].text}`);
          }
        }
      }
    }
    return issues;
  });
  expect(overlaps).toEqual([]);
}

async function serveWorkerScenario(page, workers) {
  const payload = structuredClone(fixture);
  payload.data.workers = workers;
  await page.route('**/data.json**', (route) => route.fulfill({ json: payload }));
}

const WORKER_VIEWPORTS = [
  { name: 'desktop', viewport: { width: 1440, height: 1000 } },
  { name: 'tablet', viewport: { width: 768, height: 1024 } },
  { name: 'mobile', viewport: { width: 390, height: 844 } },
];

for (const [scenarioName, workers] of Object.entries({ ...WORKER_SCENARIOS, ...MIXED_WORKER_SCENARIOS })) {
  test(`worker scenario ${scenarioName} remains readable across all viewports`, async ({ page }) => {
    await serveWorkerScenario(page, workers);
    await page.goto(baseUrl, { waitUntil: 'networkidle' });
    await expect(page.locator('#workersTable tr')).toHaveCount(workers.length);
    await expect(page.locator('#workersTable')).toContainText('Recently offline');
    await expect(page.locator('#workersTable')).toContainText('Offline');

    for (const { viewport } of WORKER_VIEWPORTS) {
      await page.setViewportSize(viewport);
      await page.waitForTimeout(150); // Allow Chart.js and CSS grid to complete responsive layout.
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `${scenarioName}/${viewport.width}px document overflow`).toBe(true);
      await expectNoHeaderOrWorkerTableOverlap(page);
    }
  });
}

test('captures every theme across desktop, tablet and mobile without visual collisions', async ({ page }, testInfo) => {
  const viewports = [
    { name: 'desktop', viewport: { width: 1440, height: 1000 } },
    { name: 'tablet', viewport: { width: 768, height: 1024 } },
    { name: 'mobile', viewport: { width: 390, height: 844 } },
  ];

  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  for (const preset of Object.keys(DASHBOARD_THEMES)) {
    for (const { name, viewport } of viewports) {
      await page.setViewportSize(viewport);
      await page.locator('#themeMenuToggle').click();
      await page.locator('#dashboardTheme').selectOption(preset);
      await expect(page.locator('#themePopover')).toBeHidden();
      await page.waitForTimeout(300); // Let theme color transitions settle before capture.
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      await expectNoHeaderOrWorkerTableOverlap(page);
      await page.screenshot({ path: testInfo.outputPath(`${preset}-${name}.png`), fullPage: true });
    }
  }
});
