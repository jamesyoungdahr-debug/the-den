# HoltOS Glass — component spec

Version 2 of the HoltOS component layer, as drawn in the redesign mockups
(https://claude.ai/code/artifact/ea042508-1ad1-4d27-b098-6f35a520f81b) and specified in
`docs/ui-redesign-plan.md`. Every value here is a token from `design/tokens.json`; the web
implementation is `app/static/den.css` (class names below), the KDE client mirrors the names
as QML components, Android as composables. Existing v1 components (`Button`, `StatusPill`,
`Panel`, `MediaTile`, `RingMark`, `Lockup`, `PoolMeter`, `ProgressRow`, `SelectRow`,
`ServiceIcon`, `OtterMark`) keep working; the mapping to v2 is noted per component.

## Surface levels

| Level | Token recipe | Web class |
|---|---|---|
| Ground | `deep` + ambient layer: `ambient-glow-current` radial (700×420 at 72% / −8%), `ambient-glow-healthy` radial bottom-left, 1–2 `ambient-ring` hairline circles off the top-right. Media pages: the item's backdrop blurred 40px at 35%, faded to deep. | `.holt-ground` (+ `.holt-ground-media` with `--backdrop` var) |
| Glass panel | `glass-surface` · `backdrop-filter: blur(glass-blur) saturate(glass-saturate)` · 1px `glass-border` · inset 1px `glass-highlight` · `shadow-1` | `.holt-glass` |
| Floating glass | `glass-surface-strong` · `blur(glass-blur-strong)` · `glass-border-strong` · `glass-highlight-strong` · `shadow-3` · `radius-lg` | `.holt-glass-float` |
| Opaque panel (no art behind it) | `surface` / `raised`, `hairline`, `radius-lg` | `.holt-panel` (v1, unchanged) |

Reduced transparency is handled at the token level (`holt-tokens.css` swaps the glass
tokens for opaque values), so components never need their own media query.

## Shell

**Sidebar** `.holt-sidebar` — width `size-sidebar` (240) or `size-sidebar-rail` (72) with
`.is-rail`; glass panel, no top/bottom/left border; padding `space-4 space-3`; contains
`Lockup`, nav groups, a flexible spacer, and the user card. Nav group: `.holt-nav` with a
`.holt-eyebrow` header at `ink-28`; items `.holt-nav a` 9×12 padding, `radius-sm`, `label`
type at `ink-55`, 18px stroke icons; active: `current` text, `current-tint` background,
2px `current` bar at −16px left. The ADMIN group is rendered only for admins.
User card: `raised`-toned pill with `Avatar`, name (`label`), role in `meta`.

**TopBar** `.holt-topbar` — height `size-top-bar` (60), glass, bottom border only;
contains the search field (`.holt-search`, `glass-input-surface`, `hairline-strong`,
`radius-md`, 9×12 padding, 13px, `ink-42` placeholder, max-width 520), a spacer, the page's
**one** primary action, then `Avatar`.

**TabBar** `.holt-tabbar` — mobile replacement for the sidebar under
`size-mobile-breakpoint` (900): height `size-tab-bar` (72), glass, top border only; four
`.holt-tab` items (icon 22px + 10.5px/700 label, min-height `size-hit-target`); active item
`current` with a `current-tint` icon pill.

**Page header** — `.holt-page-title` (`pageTitle` type) with a `meta` summary line beneath;
right-aligned filter `Chips` and view toggles.

## Content

**PosterCard** `.holt-card` — column, gap 8; `.holt-poster` 2:3 at `size-poster-*`
(sm 112, md 132, lg 148, xl 220), `radius-md`, `hairline` border, `shadow-2`; the striped
placeholder overlay stays until real art loads (`ambient-stripe`); `Badge` top-left at 8px;
optional progress bar under the poster for downloading items; title 11.5–12px/700
ellipsised; `meta` line. States: hover (lift 2px, border `current`, actions overlay with a
`scrim-strong` gradient and stacked `Button`s), selected, skeleton (`.is-skeleton` shimmer
at `raised`). Maps v1 `MediaTile`.

**Rail** `.holt-rail` — horizontal flex, gap `space-3`, `overflow-x: auto`, scroll-snap,
right-edge mask fade at 94%; header row with `eyebrow` + a `meta` "see all" link.

**Hero** `.holt-hero` — height 320 (web) / 250 (KDE) / 300 (phone), `radius-lg`, backdrop
art, `scrim-strong→scrim-weak` horizontal + vertical gradients, content bottom-left with
`eyebrow`, `display` title, `meta` facts, 14px `ink-70` overview (max 560), actions row
(`Button` primary + secondary + `Badge` solid).

**Badge** `.holt-badge` — evolves v1 `StatusPill`: 6px dot + `meta`-sized mono label;
variants `available` (`badge-available`), `pending`/`processing` (`badge-pending`),
`partial`/`error` (`badge-partial`), `missing` (`badge-missing` text, `badge-missing-dot`
dot). `.holt-badge-solid` for use over art: `glass-badge-surface`, `hairline`, 6×11
padding, `blur(glass-blur-badge)`.

**Button** `.holt-btn` — 10×20 padding, `button` type, `radius-sm`; `-primary` (`current`
fill, `deep` text, 800), `-secondary` (4% white fill, `ink-70`, `hairline-strong`),
`-quiet` (transparent, `ink-55`); `-sm` 8×14 / 12px. One primary per screen.

**Chip** `.holt-chip` — filter/tab pill: 7×12 padding, 12px/700, `ink-55`,
`hairline-strong`, 3% white fill; `.is-on` = `current` fill + `deep` text.

**Row** `.holt-row` — list row (requests, downloads, indexers): `raised` at 55% over
glass or opaque `raised` on panels, 1.5px `hairline`, `radius-md`+2, 12×16 padding; slots:
thumb (44×66 poster), main (title 13.5/700 + `meta`), fixed-width columns, `Badge`,
actions. `.is-pending` border `current` at 45%.

**Progress** `.holt-progress` — 5px track at 9% white, `radius` 3, fill `current`
(`healthy` when finished, `warning` on error); fills animate over `dur-base` `ease-out`;
never indeterminate — use `Skeleton` for unknown.

**Stat** `.holt-stat` — engine/session tiles: `eyebrow` at `ink-28`, 22px/800 value,
optional mini bar chart (6px bars, `current` or `healthy`).

**Dialog** `.holt-dialog` — native `<dialog>` styled as floating glass, 400–560 wide,
`space-5` padding, `::backdrop` = `scrim-mid` blur 6px; opens by scaling from 96% over
`dur-base`. Season picker: rows of `Checkbox` + season name + `meta` episode count +
`Badge`, primary "Request selected seasons".

**Toast** `.holt-toast` — floating glass, bottom-right, `meta` icon + 13px text, auto-dismiss
4s, slides up over `dur-base`.

**Field** `.holt-field` — v1 unchanged: `fieldLabel` mono uppercase label, input on
`glass-input-surface`/`deep`, `hairline-strong`, `radius-sm`, 9×12 padding, `current` focus
border. `Checkbox` 16px, `radius` 4, `current` when on.

**Avatar** `.holt-avatar` — `size-avatar` (28) circle, `current→healthy` gradient, `deep`
initial at 11px/900; 24px variant over posters.

**Skeleton** `.holt-skeleton` — `raised` block with a moving highlight (`glass-highlight`)
over `dur-draw`; poster-shaped in grids, line-shaped in lists. The only loading indicator.

**EmptyState** `.holt-empty` — centred, `OtterMark` at 38px+ (one sticker), a `title`-sized
line in plain language ("Nothing waiting on you"), a `body` line, at most one quiet action.

**Table** `.holt-table` — admin lists (users, indexers): `eyebrow` column headers, rows as
`Row`, sticky header on scroll.

## Motion rules

`dur-fast` 160ms for hover/focus, `dur-base` 220ms for enter/exit and progress, `dur-draw`
1600ms for the boot/loading ring; all on `ease-out`. Nothing spins. Reduced motion zeroes
the durations at the token level.

## Icons

Stroke icons on a 24 grid, 1.8 stroke, round caps/joins, `currentColor`; 18px in nav,
16px in buttons, 22px in the tab bar. Inline SVG, never emoji.
