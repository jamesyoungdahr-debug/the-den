# Status

## Last completed
M7: settings screen. `SettingsController` (plain `QObject` with NOTIFY-backed Qt
Properties, not a list model — one record) + `SettingsPage.qml` (plain
`Kirigami.FormLayout`, no `ListView`). Backend JSON API was already done. Verified the
security-relevant behavior specifically, not just assumed it: a blank secret field on
save leaves the stored value untouched rather than wiping it — tested by actually
saving a real TMDB key, then saving again with that field blank, confirming it stayed
set. Before that: M6 (calendar), M5 (TV library + generalized candidates), M4, M3 (+
the id-scoping bug fix), M2, the design system, M0/M1, and repo branding.

## Currently working on
Nothing in progress — M7 is finished, tested for real, committed, and pushed.

## Next steps
- **M8** (final milestone): Flatpak packaging (`org.kde.Platform`, `flatpak-builder`,
  verified with a real build+run). This is the one that actually matters for the
  user's stated goal — pulling this into the main HoltOS distro. All 7 feature
  milestones are now done; M8 is what's left before the client is genuinely "done."
- Known backend gaps (not fixed here, belong in the-den): `tmdb.search_movie()` 500s
  on a bad key; `GET /series/{id}/episodes` doesn't 404 on a nonexistent series id.
- Known client-side gap: no `QAbstractListModel` subclass guards against out-of-order
  replies from rapid repeated `load()`/`refresh()` calls.
- Known testing-process gap: regression scripts assume shared pre-seeded fixtures
  rather than self-seeding (see M6 in ROADMAP.md).
- Still no real visual look at the app on an actual screen (no VM/display this
  session). M8's Flatpak build, run on the real distro, should finally allow that.
