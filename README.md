# The Den Client

A native KDE desktop app (Qt6 + QML + Kirigami) for [The Den](
https://github.com/jamesyoungdahr-debug/the-den) — talks to its JSON API instead of
using a browser. See [ROADMAP.md](ROADMAP.md) for how it's being built.

## Running it for development

Needs PySide6 and KDE's Kirigami QML modules. On Arch:

```bash
sudo pacman -S python-pyside6 kirigami qqc2-desktop-style
```

Then:

```bash
QT_QUICK_CONTROLS_STYLE=org.kde.desktop python src/main.py
```

Point it at a running The Den backend (defaults to `http://127.0.0.1:8686`) and hit
Connect.
