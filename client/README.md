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

Needs PySide6 and KDE's Kirigami QML modules. On Arch:

```bash
sudo pacman -S pyside6 kirigami qqc2-desktop-style
```

Then:

```bash
QT_QUICK_CONTROLS_STYLE=org.kde.desktop python src/main.py
```

Point it at a running The Den backend (defaults to `http://127.0.0.1:8686`) and hit
Connect.

## Design

Styled to the same HoltOS design system as the-den's web UI, translated into Qt's
theming model instead of CSS — see `src/theme.py` and the "Post-M1 addition" section of
[ROADMAP.md](ROADMAP.md) for how and why.
