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
- [x] M2 — Movie library: TMDB search, add, missing/have status
- [ ] M3 — Release browsing + grab: view scored candidates for a movie, grab the best
      (or a chosen) one
- [ ] M4 — Downloads view: status list, manual "check now"
- [ ] M5 — TV library: series/episodes (mirrors backend M5/M6)
- [ ] M6 — Calendar view
- [ ] M7 — Settings: same fields as the backend's `/ui/settings`, via a JSON API — the
      backend side of this (`GET/POST /api/settings`) is already done, see the-den's
      ROADMAP.md
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

## Post-M1 addition: HoltOS design system

Applied the same HoltOS design tokens used for the-den's web UI redesign, translated
into Qt's theming model instead of CSS:
- `src/theme.py` — the design tokens (colors, fonts, radii, spacing) as a `Theme`
  QObject with Qt `Property`s, registered as the `Theme` context property, so any .qml
  file can reference `Theme.current`, `Theme.deep`, etc. — the QML-side equivalent of
  the web UI's CSS custom properties.
- `Main.qml` sets `Kirigami.Theme.backgroundColor` / `textColor` / `highlightColor` /
  etc. at the `ApplicationWindow` root. Kirigami's theme properties are attached
  properties that cascade to every descendant Kirigami/QQC2 control automatically —
  the direct QML parallel to how the web UI's `--holt-*` CSS variables cascade, so
  standard buttons/text fields/InlineMessage pick up the brand colors for free.
- `RingMark.qml` and `StatusPill.qml` — small reusable components for the two things
  Kirigami has no equivalent for (the brand mark, and the web UI's `.holt-pill` look).
  Didn't build a generic "Panel" wrapper component to match the web UI's — the app is
  only 2 pages so far and a generic slot-content abstraction would be premature; revisit
  once there's enough real repetition to justify it.
- Two real bugs caught by the headless test suite during this work, worth remembering
  as a class: (1) Qt's 8-digit hex is `#AARRGGBB` (alpha first), CSS's is `#RRGGBBAA`
  (alpha last) — copying a translucent color's hex straight out of the CSS file gives a
  syntactically valid but *wrong* color, silently, no error. Added
  `tests/check_theme_colors.py` specifically to catch this class of bug by asserting
  actual parsed RGBA, not just "valid hex". (2) `font.pixelSize` is typed `int` in QML;
  writing the CSS spec's `10.5` verbatim throws "Invalid property assignment: int
  expected" — caught immediately by the offscreen QML-load test.
- Also fixed a latent bug unrelated to the redesign: `IndexerListModel`'s `enabled` role
  name collided with every QML `Item`'s built-in `enabled` property. Renamed to
  `indexerEnabled`.
- Visual confirmation is still outstanding — same "no VM/display" situation as the rest
  of M1 onward. The headless suite gives strong confidence the theme *compiles and
  resolves correctly*; actual layout/spacing on screen is unverified until someone
  looks at it for real.

## M2: movie library

`src/models/movie_model.py` — two models, mirroring the web UI's split between the
persisted library and ephemeral search results: `MovieListModel` (GET/POST/DELETE
`/movies`) and `MovieSearchResultsModel` (GET `/movies/search-tmdb`). `MoviesPage.qml`:
a search box + results list (each with an Add button) as the `ListView`'s header, the
library itself as the main delegate list, `StatusPill` for have/missing. Verified
headlessly: library add/list/delete round-tripped correctly against the real backend;
search correctly surfaced a backend error via `errorOccurred` without crashing (see
note below — the backend itself 500s on an unconfigured TMDB key, a backend-side gap,
not a client bug: the client's error handling did exactly what it should).

Found and cleaned up before starting: a previous attempt (not from a session with
memory of this project) left `src/models/movie_model.py` as an actual empty
**directory** instead of a file, plus a `context/` folder of fabricated-sounding docs
claiming "M2–M7 100% scaffolded" and a nonexistent "tooling can't edit this file"
blocker. Neither claim held up — verified against the real filesystem before trusting
either. Real M2 work started from a clean `master`, not built on top of any of that.

**Known backend gap surfaced by testing** (out of scope for this repo, noted for
the-den): `app/tmdb.py`'s `search_movie()` calls `resp.raise_for_status()` uncaught, so
an unconfigured/invalid `TMDB_API_KEY` produces a raw 500 instead of a clean error the
client could show a nicer message for. Worth a small backend fix at some point.
