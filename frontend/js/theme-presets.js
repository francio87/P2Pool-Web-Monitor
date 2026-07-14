export const DASHBOARD_THEMES = Object.freeze({
  'classic-light': Object.freeze({ dashboardTheme: 'classic', colorMode: 'light' }),
  'classic-dark': Object.freeze({ dashboardTheme: 'classic', colorMode: 'dark' }),
  'market-dark': Object.freeze({ dashboardTheme: 'market-dark', colorMode: 'dark' }),
});

export function resolveDashboardTheme(theme, legacyColorMode = 'dark') {
  if (Object.hasOwn(DASHBOARD_THEMES, theme)) return theme;
  return legacyColorMode === 'light' ? 'classic-light' : 'classic-dark';
}
