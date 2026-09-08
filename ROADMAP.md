# The Den Client — Roadmap

A native KDE (Qt6/QML/Kirigami) desktop app that talks to a running [The Den](
https://github.com/jamesyoungdahr-debug/the-den) backend over its existing JSON API,
as an alternative to using the web UI in a browser. Packaged as a Flatpak using the KDE
runtime. Deliberately a **separate repo** from the backend so the two can be released
and updated independently — the client only depends on the backend's HTTP API staying
stable, not on its internals.

Built the same way as the backend: one milestone at a time, tested before moving on.

## Milestones

- [x] M0 — Skeleton: Kirigami window boots, "Connect" button hits `/health`, shows
      connected/not-connected status
- [x] M1 — Indexers: list/add/delete/test-connection (mirrors the backend's `/indexers`)
- [ ] M2 — Movie library: TMDB search, add, missing/have status
- [ ] M3 — Release browsing + grab: view scored candidates for a movie, grab the best
      (or a chosen) one
- [ ] M4 — Downloads view: status list, manual "check now"
- [ ] M5 — TV library: series/episodes (mirrors backend M5/M6)
- [ ] M6 — Calendar view
- [ ] M7 — Settings: same fields as the backend's `/ui/settings`, via a JSON API
      (needs a small backend addition — it currently only exposes settings as an HTML
      form, not JSON; add a `GET/POST /api/settings` alongside the existing UI route)
- [ ] M8 — Flatpak packaging: manifest using `org.kde.Platform`, build via
      `flatpak-builder`, verified with a real build+run

## Notes

- No auth on the backend (see the-den's ROADMAP) — same caveat applies here: fine on
  localhost/LAN, the client doesn't add authentication either.
- Network calls use `QNetworkAccessManager` (Qt's own async HTTP client) rather than a
  Python HTTP library, so requests never block the UI thread.
- M0 was visually confirmed running via WSLg (WSL2's GUI passthrough). From M1 onward,
  without a VM/display available, testing shifted to two headless techniques that don't
  need any GUI at all:
  1. `QCoreApplication` (no display) to exercise Python/network model logic against the
     real backend — see `tests/check_indexer_model.py`. Catches wrong URLs, bad JSON,
     wrong Qt enum usage, etc.
  2. `QT_QPA_PLATFORM=offscreen` to force Qt to actually compile and load `.qml` files
     (catching import errors, unknown properties, bad role-name bindings) without
     rendering pixels — see `tests/check_indexers_page_qml.py`. Since QML pages are
     lazily compiled (`pageStack.push()` doesn't run until clicked), each new page needs
     its own such script that loads it directly, not just `Main.qml`.
  These two together catch nearly everything a screenshot would (JSON/network wiring,
  Python↔QML binding correctness) — the one thing they can't catch is visual layout
  problems (overlapping widgets, bad spacing), which still needs an eventual real look.
