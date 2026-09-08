# Status

## Last completed
All 7 feature milestones (M0–M7) are done: connect, indexers, movie library,
release/grab (movies + episodes via one generalized model), downloads, TV library,
calendar, settings. Every milestone tested for real against a running backend, not
just headlessly-happy-path — see ROADMAP.md for the M3 id-scoping bug fix (affected
M1/M2 too) and the testing discipline that came out of it.

M8 (Flatpak packaging) was started, hit real but solvable friction (PySide6 not
bundled in the KDE runtime, wheel files too large for git, flatpak sandbox
network/filesystem/permission quirks), then abandoned mid-attempt at the user's
request. Nothing was committed for it. Full account of what was tried is in
ROADMAP.md's "M8" section.

## Currently working on
Nothing in progress. Packaging approach is an open question.

## Next steps
- **Decide how this actually gets packaged/distributed** — the thing standing between
  "feature complete" and "pulled into the main HoltOS distro," which was the whole
  point of doing M8. Options include: try Flatpak again (now with a plan for the
  wheel-size and sandbox issues already known), or a native Arch package (matching
  how the-den's own `PKGBUILD` already works, and arguably more consistent for a
  HoltOS-only app not meant to run on other distros).
- Known backend gaps (not fixed here, belong in the-den): `tmdb.search_movie()` 500s
  on a bad key; `GET /series/{id}/episodes` doesn't 404 on a nonexistent series id.
- Known client-side gap: no `QAbstractListModel` subclass guards against out-of-order
  replies from rapid repeated `load()`/`refresh()` calls.
- Known testing-process gap: regression scripts assume shared pre-seeded fixtures
  rather than self-seeding (see M6 in ROADMAP.md).
- Still no real visual look at the app on an actual screen (no VM/display this
  session). Whatever packaging approach is chosen, running the built app for real is
  the way to finally get one.
