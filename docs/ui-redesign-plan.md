# Plan: UI redesign across web, KDE, and Android -- "HoltOS Glass"

Status: **planned, not started.** Written 2026-09-11. Mockups of the eight key frames (web
Discover, series detail, Requests, Movies library, Downloads, Sign in; KDE and Android
Discover) are on the design canvas:
https://claude.ai/code/artifact/ea042508-1ad1-4d27-b098-6f35a520f81b -- they are the
reference for U0/U1 below. Companion to
[requests-plan.md](requests-plan.md) (M11): the Discover/Requests work should be built
*in* this design, not retrofitted to it, so this plan's shell and component work is
sequenced ahead of M11's pages.

## Brief (decided 2026-09-11)

- **Keep the HoltOS brand** -- palette, Nunito + JetBrains Mono, the otter, the six
  principles in `design/foundations/principles.html` -- but make the interface feel
  modern: layered, translucent "glass" surfaces with blur, media-first layouts driven
  by poster and backdrop art, and motion that reads as progress.
- **Left sidebar** app shell instead of today's top nav.
- Every surface gets it: the web UI, the KDE client, and the Android app. The two
  native clients are the weak point today ("super clunky"): copy-pasted page
  boilerplate, plain list rows for everything, no imagery, no shared layout.
- Deliverable for now is this plan. Mockups (a design canvas you can tweak) are the
  natural next step before code; see "What next" at the bottom.

## What's wrong today (honest inventory)

| Surface | State |
|---|---|
| Web UI | HoltOS tokens applied, but every page is the same recipe: page title, flat panel, list of rows, form at the bottom. No posters (striped placeholders), no hierarchy between admin plumbing and everyday use, top nav that will not scale to Discover/Requests/Users/Plex. The new Downloads page is the closest to the target. |
| KDE client (PySide6/Kirigami) | Functional mirror of the web pages: a `ListView` of `SwipeListItem`s per page, an error banner copy-pasted seven times, a pushed page per action. No imagery, no dashboard, default Kirigami look with brand colours dropped in. Never seen on a screen since M0. |
| Android (Compose/M3) | Same shape: Connect screen with nav buttons, list screens, settings form. Material 3 defaults with HoltOS colours. Four of eight milestones unbuilt, so there is little to preserve. |

## Design language: HoltOS Glass

Additions to the design system, layered on the existing tokens rather than replacing them.

### Surfaces and depth

Three levels, each a real z-layer, not just a colour:

| Level | Use | Web recipe |
|---|---|---|
| **Ground** | page background | `--holt-deep` plus an *ambient layer*: on media pages the current item's backdrop (blurred 40px, 35% opacity, faded to deep with a gradient); elsewhere a faint radial purple glow and the wallpaper's ellipse shapes from `design/assets/` at ~5% |
| **Glass panel** | cards, sidebar, top bar, filter bars | `background: color-mix(in srgb, var(--holt-surface) 70%, transparent); backdrop-filter: blur(18px) saturate(140%); border: 1px solid var(--holt-hairline); box-shadow: inset 0 1px 0 rgba(255,255,255,.06), var(--holt-shadow)` |
| **Floating glass** | dialogs, menus, toasts, hover cards | same, `blur(28px)`, 82% surface, stronger shadow, `--holt-radius-lg` |

Rules that keep it tasteful and fast:

- **Glass only over something worth blurring.** A panel sitting on flat `--holt-deep`
  is just an opaque panel (`--holt-surface`); glass is for the sidebar/top bar over
  scrolling content, cards over backdrop art, and floating layers. Cap it at ~3
  blurred layers on screen at once.
- **Text never sits directly on a poster or backdrop.** Always a scrim
  (`linear-gradient` to deep) or a glass panel underneath.
- **Reduced transparency and motion are first-class.**
  `@media (prefers-reduced-transparency: reduce)` swaps every glass recipe for the
  opaque surface (progressive enhancement: the query is newer, so the opaque
  fallback is also what unsupported browsers see when the query is ignored -- write
  the opaque values in a class that the glass class overrides only when the query
  is *not* set to reduce). `@media (prefers-reduced-motion: reduce)` drops all
  transitions to 0.
- **Browser support policy** (proposal, record in CLAUDE.md later): Baseline widely
  available features are used freely -- `backdrop-filter`, `color-mix()`,
  container queries, `:has()`, `<dialog>`, CSS nesting. Newly available ones
  (`@starting-style`, view transitions, anchor positioning) only as enhancements with
  the plain behaviour as fallback. The app runs on the HoltOS desktop's browser and
  phones, so no legacy targets.
- **Performance**: blur radius halves below 700px wide; `contain: paint` on glass
  panels; never animate `backdrop-filter` itself; large poster grids use
  `content-visibility: auto`; images get `loading="lazy"` and fixed aspect ratios so
  nothing reflows.

### Colour and type

Unchanged tokens (`holt-tokens.css`). New semantic tokens on top:

```
--glass-surface, --glass-surface-strong, --glass-border, --glass-highlight
--scrim-media (gradient over art), --glow-current (ambient radial)
--badge-available (healthy), --badge-pending (current), --badge-partial (warning), --badge-missing (ink-28)
--elevation-1/2/3 (shadows), --dur-fast 160ms / --dur-base 220ms / --ease-out cubic-bezier(.2,.8,.2,1)
```

Type roles stay; add `--holt-display-lg` (42px/900) for detail-page titles over art.

### Motion

Principle 04 ("drawn, never spun") applied everywhere: progress bars and rings draw;
loading is a **skeleton** (poster-shaped shimmer) never a spinner; page changes
cross-fade content (view transitions where available); hover lifts a card 2px and
brightens the border; dialogs scale from 96% with `@starting-style`. All 160–220ms.

### Imagery

TMDB posters (`w342`) and backdrops (`w1280`) are the redesign's raw material. Every
media object gets a poster; every detail page gets a backdrop; empty states get the
otter ("cute, but level": one sticker, not a mascot parade).

## App shell (web)

```
┌─────────┬──────────────────────────────────────────────┐
│ ◯ Den   │  ⌕ Search movies & shows…        [avatar ▾]  │  ← sticky glass top bar
│         ├──────────────────────────────────────────────┤
│ Discover│                                              │
│ Requests│   page content (max-width 1400, padded)      │
│ ───     │                                              │
│ Movies  │                                              │
│ TV      │                                              │
│ Calendar│                                              │
│ ─── ADMIN (admins only)                                │
│ Download│                                              │
│ Indexers│                                              │
│ Users   │                                              │
│ Settings│                                              │
│         │                                              │
│ [otter] │                                              │
└─────────┴──────────────────────────────────────────────┘
```

- **Sidebar**: 240px expanded, 72px rail (icons + tooltips) when collapsed; state
  remembered per user. Glass, sits over the ground layer so the ambient art shows
  through faintly. Lockup at the top (RingMark + wordmark), nav groups with mono
  eyebrows, the ADMIN group rendered only for admins (server-side; not just hidden).
  Active item: purple text + a 2px left bar (the existing nav-underline idea rotated).
- **Top bar**: global search that opens Discover search results; the page's single
  primary action ("one shout per screen") lives at its right when a page has one;
  avatar menu (profile/API token, logout).
- **Mobile (< 900px)**: sidebar becomes a **bottom tab bar** -- Discover, Requests,
  Library, More -- so approving a request from a phone is two taps. Top bar keeps
  search. Uses container queries on the content area, not only viewport queries, so
  cards adapt when the sidebar collapses too.

## Pages

| Page | Redesign |
|---|---|
| **Discover** (`/`, home) | Hero: the top trending item's backdrop full-bleed under the top bar, scrimmed, with title, year, one-line overview and a Request/Available badge. Below: horizontal rails (Trending, Popular movies, Upcoming, Popular series, Recent requests) of `PosterCard`s with snap scrolling and edge fade. Search results page is a responsive poster grid with type filter pills. |
| **Detail** (`/discover/movie|tv/{id}`) | Backdrop ground layer; glass info card left (poster, title in display-lg, facts row in mono, genres as pills, overview, cast rail); right column the **status/action card**: availability per source (Den library / Plex), request button or state, for TV a seasons table with per-season status and checkboxes feeding the request `<dialog>`. Recommendations rail at the bottom. |
| **Requests** | Filter pills (All / Pending / Approved / Declined / Available) + sort; each request a glass row: poster thumb, title/year, requester avatar + name, relative time, seasons chips, status badge; admins get Approve/Decline inline with optimistic update; users see their own. Empty state: otter + "Nothing waiting on you". |
| **Movies / TV library** | Poster grid (container-query sized 120–180px) with status badge and hover actions (Find releases, Remove for admins); list/grid toggle; filter by missing/have; sort. Series detail: backdrop + season accordion; episode rows with air date, have/missing pill, and a Find releases quiet button. |
| **Calendar** | Real month grid + agenda list, poster chips on days, missing vs upcoming distinguished by badge colour; week/month toggle. |
| **Downloads** (admin) | Keep the new live rows; add a session header (engine state, DHT, total rates as drawn mini-bars), group by state, and a compact add-torrent affordance in the top bar action slot. |
| **Indexers** (admin) | Table with status pill per indexer (last test result), inline test/enable/delete; add form in a dialog rather than a permanent panel. Manual release search moves here as a secondary tab. |
| **Users** (admin) | Table: avatar, name, Plex/local badge, role, limits, last login; edit in a dialog. |
| **Settings** (admin) | Sections as cards (Library, Torrent client, Plex, Notifications, Automation) with a sticky mini-index on the left; save per section; secrets keep the current "set / not set" treatment. |
| **Login / Setup** | Centred floating-glass card over the HoltOS wallpaper with the full-body otter at low opacity: "Sign in with Plex" primary, local form secondary. Setup adds the "this account becomes admin" note. |

## Component layer (web)

`app/static/den.css` grows into a small, named component layer (still plain CSS, no
framework; optional split into `den.base.css` / `den.components.css`):

`Sidebar`, `TopBar`, `GlassPanel` (panel/floating variants), `PosterCard` (sizes sm/md/lg,
status badge, hover actions, skeleton state), `Rail` (snap-scrolling row with fades),
`Hero`, `Badge` (evolves `StatusPill`: available/pending/partial/missing/error),
`Dialog` (native `<dialog>` styled as floating glass), `Toast`, `Pills` (filters/tabs),
`Table`, `Field`/`Form`, `Avatar`, `Skeleton`, `EmptyState`, `Progress` (bar + ring,
drawn). JavaScript stays vanilla and small: sidebar toggle, dialog open/close, toast
queue, rail arrows, the existing polling on Downloads/Requests.

Source of truth: extend `design/` (the React design-system source) with the new
components and tokens so the three implementations translate from one spec, and add
**`design/tokens.json`** exported to `holt-tokens.css`, the KDE `theme.py`, and the
Android `Color.kt`. Today each is hand-copied and has drifted once already (the
`#AARRGGBB` bug in the KDE client's STATUS.md).

## KDE client redesign (the-den-client)

- **Shell**: `Kirigami.ApplicationWindow` with a custom sidebar (`Kirigami.GlobalDrawer`
  in modal=false mode, or a hand-built column matching the web rail) and a page stack;
  on narrow windows Kirigami's own drawer behaviour gives the mobile pattern for free.
- **Glass**: Qt 6.5+ `QtQuick.Effects` `MultiEffect { blurEnabled: true; blur: 0.6 }`
  on a `ShaderEffectSource` of the content behind the sidebar/top bar and on detail
  page backdrops; keep it to those layers (each is a live offscreen render). Fallback
  when effects are unavailable or "reduced effects" is set: opaque `--holt-surface`.
- **Components**: a small QML component library mirroring the web names --
  `PosterCard.qml`, `Rail.qml`, `GlassPanel.qml`, `Badge.qml` (replaces `StatusPill`),
  `EmptyState.qml`, `Skeleton.qml`, `PageHeader.qml` with a single shared error/status
  banner. This is what removes the copy-pasted `Connections` + `InlineMessage` block
  from all seven pages (already flagged in its STATUS.md).
- **Pages**: Discover, detail, Requests, Login added (M11); Movies/TV become poster
  grids (`GridView` + `Image` with `cache: true` and `sourceSize`); Downloads adopts
  `/torrents` rows with `ProgressRow`-style drawn bars.
- **Fix the clunk**: one navigation model (sidebar + page stack) instead of
  Connect-then-buttons; consistent page header; keyboard focus order; window state
  remembered. And finally **look at it on a screen** -- the plan should include a real
  visual pass on the HoltOS desktop, which its STATUS.md says has never happened.

## Android redesign (the-den-android)

- **Shell**: `NavigationRail` on wide/tablet, `NavigationBar` (bottom) on phones --
  Discover, Requests, Library, More -- with the admin group behind More for admins.
  Edge-to-edge, `TopAppBar` with search.
- **Glass**: `Modifier.blur` only works on the composable itself, not what's behind
  it; for true frosted layers use the **Haze** library (`dev.chrisbanes.haze`) which
  wraps Android 12+ `RenderEffect` and degrades to a translucent scrim on older
  devices (minSdk is 26, so the fallback path matters). Apply to the bottom bar over
  scrolling grids and to detail-page backdrops; nowhere else.
- **Theme**: Material 3 `ColorScheme` from `tokens.json`; `Surface` variants for the
  three depth levels; Nunito/JetBrains Mono via `FontFamily`.
- **Components**: `PosterCard`, `Rail` (`LazyRow` with snap), `Badge`, `EmptyState`,
  `Skeleton` (shimmer), `RequestSheet` (season picker as a modal bottom sheet, the
  phone-native equivalent of the web dialog). Posters via **Coil**.
- **Motion**: Navigation Compose shared-element transitions poster→detail; drawn
  progress for downloads.
- **Roadmap consequence**: as requests-plan.md recommends, build Discover/Requests
  (the phone's real job) in this design first; the unbuilt M3–M6 admin screens come
  after and reuse the same components.

## Milestones

| Step | Scope | Size | Depends on |
|---|---|---|---|
| U0 | **Done 2026-09-11.** `design/tokens.json` is the single source; `python design/build_tokens.py` regenerates `app/static/holt-tokens.css` (reduced-transparency and reduced-motion handled at token level) plus `design/exports/holt_tokens.py` and `HoltTokens.kt` for the clients; component spec in `design/docs/glass-components.md`; mockups linked above | M | -- |
| U1 | Web shell: sidebar, top bar, mobile tab bar, ground/ambient layers, `PosterCard`/`Rail`/`Badge`/`Dialog`/`Toast`; Movies + TV pages re-laid as poster grids with real TMDB art | L | U0 |
| U2 | Remaining web pages in the new design: Downloads, Indexers, Settings, Calendar, Series detail; empty states, skeletons, reduced-motion/transparency passes | M | U1 |
| U3 | M11's new pages (Discover, detail, Requests, Login/Setup, Users) built directly on U1 components | -- | U1 + M11 backend |
| U4 | KDE client: shell + component library + poster pages + Downloads on `/torrents`; visual pass on a real desktop | L | U0, M10 API fixes |
| U5 | Android: shell + components + Discover/Requests first, then remaining screens | L | U0, M11 auth |

Suggested interleave with the M11 plan: **U0 → U1 → M11a/b (auth on the new shell) →
U2 → M11c–f → U3 → M11g**, with U4 and U5 running after the backend API for M10/M11 is
settled so the clients are redesigned once, not twice.

## Decisions still open

1. **Mockups next?** A design canvas of Discover, detail, Requests, Library, Downloads
   and Login lets you push pixels before any code. Recommended.
2. **Sidebar default**: expanded on desktop, rail on smaller laptops -- or always rail?
3. **Ambient art on non-media pages**: subtle wallpaper shapes/glow (recommended) or
   flat deep?
4. **Light theme**: HoltOS is dark-first and both clients are dark-only; propose
   staying dark-only for this pass.
5. **Companion-app order**: KDE first (it's complete and on the distro) or Android
   first (the phone is where Requests matter most)?

## Risks

- **Blur cost** on low-end hardware and older Android: strict layer budget, opaque
  fallbacks, reduced-transparency support from day one.
- **Readability over art**: scrims are mandatory; run contrast checks on the badge
  colours over posters.
- **Three implementations drifting**: `tokens.json` as the one source; components
  share names across web/QML/Compose so specs map 1:1.
- **Scope creep**: the redesign touches every page; U1's component set is the gate --
  no page is redesigned with one-off styles outside it.

## What next

If the mockups-first route is chosen, the next session produces a design canvas of
the six key screens (web) in HoltOS Glass, plus one KDE and one Android frame to show
the shell translation, and iterates on those before U0 starts.
