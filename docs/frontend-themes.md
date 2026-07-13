# Frontend themes

The dashboard supports a shared HTML/data contract with theme-specific visual layers. The current default is `classic`; future themes must remain offline-first and use local assets only.

## Theme contract

- `data-dashboard-theme` on `<html>` identifies the visual theme. It currently defaults to `classic`.
- `data-theme` remains an internal light/dark color-mode attribute, derived from the selected theme preset rather than controlled by a separate toggle.
- Each theme may override tokens, components and layout through CSS scoped to `[data-dashboard-theme="<name>"]`.
- HTML IDs, the `data.json` schema and the JavaScript rendering contract must remain stable across themes.
- Tailwind is a build-time tool only. The runtime receives compiled local CSS and JavaScript, with no CDN or Node.js dependency.

## Themes

### `classic`

The current P2Pool dashboard visual language. Its source is `frontend/themes/classic.css` and it preserves the existing light/dark palette, cards, charts and status treatments.

### `market-dark`

A first local implementation is available in `frontend/themes/market-dark.css`. The header selector exposes `Classic light`, `Classic dark` and `Market dark`; the selected preset is persisted in `localStorage` as `p2pool-dashboard-theme`.

Characteristics carried forward:

- near-black background with charcoal panels and subtle borders;
- compact, high-density information cards;
- orange as the primary live/action accent;
- green and red reserved for positive/negative operational signals;
- clear value hierarchy, optional monospaced numeric values, badges, progress bars and sparklines.

The next step is visual refinement against desktop and mobile references.
