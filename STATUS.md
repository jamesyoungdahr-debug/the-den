# Status

## Last completed
M8 (take two, after Flatpak was abandoned): native Arch package. `PKGBUILD` +
`deploy/the-den-client` (launcher) + `deploy/the-den-client.desktop` + `assets/logo.svg`
as the icon — same pattern as the-den's own packaging. Built and installed for real via
`makepkg -si` on genuine Arch (WSL2); the real installed `the-den-client` command boots
cleanly. All 7 feature milestones (M0–M7) plus this packaging milestone are now done.

Couldn't get a real on-screen screenshot despite trying (including a `wsl --shutdown`
restart specifically for this) — WSLg's compositor won't connect from this harness's
non-interactive invocations, a different and more specific limitation than the general
"no VM/display" noted throughout earlier milestones. Full account in ROADMAP.md's
"M8, take two" section.

## Currently working on
Nothing in progress. The app is feature-complete and packaged.

## Next steps
- **Get a real look at it.** The one thing left that this dev environment genuinely
  cannot provide: install the package (or just `makepkg -si` from this repo) on the
  actual HoltOS target hardware/VM and see it run for real — spacing, layout, does it
  actually look like the design intent.
- Known backend gaps (not fixed here, belong in the-den): `tmdb.search_movie()` 500s
  on a bad key; `GET /series/{id}/episodes` doesn't 404 on a nonexistent series id.
- Known client-side gap: no `QAbstractListModel` subclass guards against out-of-order
  replies from rapid repeated `load()`/`refresh()` calls.
- Known testing-process gap: regression scripts assume shared pre-seeded fixtures
  rather than self-seeding (see M6 in ROADMAP.md).
- If Flatpak distribution is wanted later too (e.g. for non-HoltOS use), the M8
  attempt notes in ROADMAP.md capture exactly where that got stuck and why.
