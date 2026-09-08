# The Den Client

A native KDE desktop app (Qt6 + QML + Kirigami) for [The Den](
https://github.com/jamesyoungdahr-debug/the-den) — talks to its JSON API instead of
using a browser. See [ROADMAP.md](ROADMAP.md) for how it's being built.

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
