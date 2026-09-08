# Status

## Last completed
M5: TV library. `SeriesListModel`/`SeriesSearchResultsModel`/`EpisodesModel` +
`SeriesPage.qml`/`EpisodesPage.qml` (season-grouped via `ListView.section`).
Generalized `CandidatesModel`/`CandidatesPage.qml` to serve both movies and episodes
(one `resource` param, one `candidatesSource` override) rather than duplicating the
whole page — verified both variants load real, independent data correctly. Two more
test-design bugs caught while building this (a backend endpoint that doesn't 404 on a
bad id, and a property-seeding race in the test harness itself) — full story in
ROADMAP.md's "M5" section. Before that: M4 (downloads), M3 (candidates/grab + the
id-scoping bug fix), M2, the design system, M0/M1, and repo branding.

## Currently working on
Nothing in progress — M5 is finished, tested for real, committed, and pushed.

## Next steps
- **M6** (next milestone): calendar view — missing movies + upcoming/missing episodes,
  mirrors the backend's `/calendar`.
- **M7** after that: settings screen. The backend's JSON API side
  (`GET/POST /api/settings`) is already done (see the-den's ROADMAP.md) — this is
  purely client-side QML/model work now.
- **M8** after that: Flatpak packaging (`org.kde.Platform`, `flatpak-builder`,
  verified with a real build+run) — this is the one the user actually needs, to pull
  the client into the main HoltOS distro.
- Consider whether the earlier `check_*_page_qml.py` scripts should switch to
  `engine.setInitialProperties()` before `load()` instead of `root.setProperty()`
  after — see M5's note in ROADMAP.md for why this matters.
- Known backend gaps (not fixed here, belong in the-den): `tmdb.search_movie()` 500s
  on a bad key; `GET /series/{id}/episodes` doesn't 404 on a nonexistent series id.
- Known client-side gap: no `QAbstractListModel` subclass guards against out-of-order
  replies from rapid repeated `load()`/`refresh()` calls. Not an issue today (every
  real navigation calls `load()` once), but worth hardening eventually.
- Still no real visual look at the app on an actual screen (no VM/display this
  session). Headless tests cover network/data correctness thoroughly — the remaining
  gap is purely visual/layout polish, which M8's Flatpak build (run on the real distro)
  should finally let someone check.
