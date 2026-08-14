import assert from 'node:assert/strict';
import test from 'node:test';

import {
  asNumber,
  formatAgeSeconds,
  formatSidechain,
  formatWorkerHashrate,
  humanizeReason,
} from '../frontend/js/components.js';
import { DASHBOARD_THEMES, resolveDashboardTheme } from '../frontend/js/theme-presets.js';

test('formatting helpers handle invalid and boundary values', () => {
  assert.equal(asNumber('not-a-number'), 0);
  assert.equal(asNumber('12.5'), 12.5);
  assert.equal(formatWorkerHashrate(999), '999 H/s');
  assert.equal(formatWorkerHashrate(12500), '12.50 KH/s');
  assert.equal(formatAgeSeconds(59), '59s');
  assert.equal(formatAgeSeconds(3600), '1h');
  assert.equal(formatSidechain(' MINI '), 'mini');
});

test('reason labels preserve known and unknown values', () => {
  assert.equal(humanizeReason('warming_up'), 'Not enough mining samples yet');
  assert.equal(humanizeReason('unknown_reason'), 'unknown_reason');
});

test('theme presets preserve supported values and migrate legacy preferences', () => {
  assert.deepEqual(DASHBOARD_THEMES['market-dark'], {
    dashboardTheme: 'market-dark',
    colorMode: 'dark',
  });
  assert.equal(resolveDashboardTheme('classic-light'), 'classic-light');
  assert.equal(resolveDashboardTheme('classic', 'light'), 'classic-light');
  assert.equal(resolveDashboardTheme('classic', 'dark'), 'classic-dark');
  assert.equal(resolveDashboardTheme('unknown', 'dark'), 'classic-dark');
});
