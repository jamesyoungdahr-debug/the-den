# Status

## Last completed
M6: calendar view. `CalendarMoviesModel`/`CalendarEpisodesModel` compose the view
client-side from `/movies` and `/series/{id}/episodes` (no `/calendar` JSON endpoint
exists on the backend) — the episodes model does a real fan-out/fan-in over N series'
worth of requests. `CalendarPage.qml` uses plain `Repeater`s in a `ColumnLayout`, no
`ListView.header` involved, so the M3 scoping bug's precondition doesn't even apply
here. Verified against real aggregated, sorted data plus a forced real network error.
Also surfaced (and worked around) a testing-process gap: the regression scripts assume
shared pre-seeded fixture state rather than being self-contained — noted in
ROADMAP.md's M6 section for whenever this gets a real CI pipeline. Before that: M5 (TV
library + generalized candidates), M4, M3 (+ the id-scoping bug fix), M2, the design
system, M0/M1, and repo branding.

## Currently working on
Nothing in progress — M6 is finished, tested for real, committed, and pushed.

## Next steps
- **M7** (next milestone): settings screen. Backend JSON API side is already done
  (`GET/POST /api/settings`, see the-den's ROADMAP.md) — purely client QML/model work.
- **M8** after that: Flatpak packaging (`org.kde.Platform`, `flatpak-builder`, verified
  with a real build+run) — the one that actually matters for pulling this into the
  main HoltOS distro, per the user's stated goal.
- Known backend gaps (not fixed here, belong in the-den): `tmdb.search_movie()` 500s
  on a bad key; `GET /series/{id}/episodes` doesn't 404 on a nonexistent series id.
- Known client-side gap: no `QAbstractListModel` subclass guards against out-of-order
  replies from rapid repeated `load()`/`refresh()` calls.
- Known testing-process gap: regression scripts assume shared pre-seeded fixtures
  rather than self-seeding (see M6 in ROADMAP.md).
- Still no real visual look at the app on an actual screen (no VM/display this
  session). M8's Flatpak build, run on the real distro, should finally allow that.
