<p align="center">
  <img src="assets/logo.svg" width="72" alt="The Den">
</p>
<h1 align="center">The Den Client</h1>
<p align="center"><code>PART OF HOLTOS</code></p>

A native KDE desktop app (Qt6 + QML + Kirigami) for [The Den](../README.md) — talks to
its JSON API instead of using a browser. See [ROADMAP.md](ROADMAP.md) for how it's being
built and [STATUS.md](STATUS.md) for what's done/next right now.

Since 2026-09-12 the client lives in the main repo under `client/` (merged from the old
`the-den-client` repo with its history), so server and client ship from one release tag
and share the HoltOS design tokens in [`../design/`](../design/). Commands below are run
from this `client/` directory.

## Running it for development
Needs the system PySide6 (the pip wheel bundles its own Qt, which can't load the distro's
Kirigami plugin) plus KDE's Kirigami QML modules. On Arch:

```bash
sudo pacman -S pyside6 kirigami qqc2-desktop-style qt6-declarative ttf-nunito ttf-jetbrains-mono
```

On Ubuntu 24.04+:

```bash
sudo apt install python3-pyside6.qtqml python3-pyside6.qtquick python3-pyside6.qtnetwork python3-pyside6.qtquickcontrols2 \
  qml6-module-org-kde-kirigami qml6-module-org-kde-desktop qml6-module-qtquick-controls qml6-module-qtquick-layouts \
  qml6-module-qtquick-shapes qml6-module-qtquick-effects fonts-nunito
```

Then:

```bash
QT_QUICK_CONTROLS_STYLE=org.kde.desktop python3 src/main.py
```

Point it at a running The Den backend (defaults to `http://127.0.0.1:8686`). If the
server requires sign-in, use **Sign in with Plex** (opens plex.tv in your browser) or a
local account; the client swaps the session for a personal API token and keeps only
that, in `QSettings`, sent as `X-Api-Key`. While sign-in is optional on the server, an
anonymous connection is an admin and everything works without an account.

## Layout

- `src/api_client.py` -- the one connection: base URL, token, sign-in (local + Plex PIN),
  who-am-I, and the `request()` helper every model goes through.
- `src/models/base.py` -- `JsonListModel` / `JsonRecord`: declare `FIELDS` + `PATH`,
  get roles, fetching, the out-of-order-reply guard, `loading`/`count`, `get(row)`.
  The other files under `src/models/` are thin subclasses (library, episodes,
  candidates, indexers, calendar, torrents, settings, Discover rails/search/detail,
  requests).
- `src/theme.py` -- the HoltOS Glass tokens as the QML `Theme` context property, read
  from `../design/exports/holt_tokens.py` (the package copies it in).
- `src/qml/holt/` -- the component library: `GlassPanel`, `Ground`, `Badge`,
  `PosterCard`, `Rail`, `HoltRow`, `HoltButton`, `HoltTextField`, `Field`, `Chip`,
  `HoltDialog`, `StatusBanner`, `EmptyState`, `Skeleton`, `PageHeader`, `ProgressBar`,
  `Avatar`, `RingMark`, `Eyebrow`, `Meta`, `HoltPage`, and `Holt.js` helpers.
- `src/qml/Main.qml` -- the shell: glass sidebar (rail when narrow or collapsed), top bar
  with global search and the page's one primary action, page stack, toasts, routing to
  the login page until the server lets us browse.
- `src/qml/*Page.qml` -- Login, Discover, Search, Detail, Requests, Movies, TV,
  Episodes, Releases (Candidates), Calendar, Downloads (built-in torrent client),
  Indexers, Settings.

## Testing without a desktop

Everything runs under `QT_QPA_PLATFORM=offscreen` against a live backend:

```bash
DEN_URL=http://127.0.0.1:8686 DEN_API_TOKEN=<admin token from /ui/profile> tests/run_all.sh
```

`tests/check_*.py` drive the models directly; `tests/qml_harness.py` compiles every page
against the real model objects and fails on any QML warning; `tests/screenshot_app.py`
walks the actual app page by page and writes a PNG of each, which is how the U4 visual
pass was done before the client had ever been seen on a real screen.

## Design

Styled to the same HoltOS Glass design system as the-den's web UI, translated into Qt's
theming model instead of CSS: the tokens come from one generated file, the glass is a
translucent panel over a drawn ground layer (deep background + ambient glows) rather than
a live blur, and every control is drawn from tokens so the platform theme never leaks in.
See `../docs/ui-redesign-plan.md` for the design language and this repo's ROADMAP for
the history.
