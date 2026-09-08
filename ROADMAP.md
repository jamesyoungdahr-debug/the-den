# The Den Client — Roadmap

A native KDE (Qt6/QML/Kirigami) desktop app that talks to a running [The Den](
https://github.com/jamesyoungdahr-debug/the-den) backend over its existing JSON API,
as an alternative to using the web UI in a browser. Deliberately a **separate repo**
from the backend so the two can be released and updated independently — the client
only depends on the backend's HTTP API staying stable, not on its internals.

Built the same way as the backend: one milestone at a time, tested before moving on.

## Milestones

- [x] M0 — Skeleton: Kirigami window boots, "Connect" button hits `/health`, shows
      connected/not-connected status
- [x] M1 — Indexers: list/add/delete/test-connection (mirrors the backend's `/indexers`)
- [x] M2 — Movie library: TMDB search, add, missing/have status
- [x] M3 — Release browsing + grab: view scored candidates for a movie, grab the best
      (or a chosen) one
- [x] M4 — Downloads view: status list, manual "check now"
- [x] M5 — TV library: series/episodes (mirrors backend M5/M6)
- [x] M6 — Calendar view
- [x] M7 — Settings: same fields as the backend's `/ui/settings`, via a JSON API — the
      backend side of this (`GET/POST /api/settings`) is already done, see the-den's
      ROADMAP.md
- [ ] M8 — ~~Flatpak packaging~~ Abandoned mid-attempt — see the "M8" note below.
      Packaging approach still undecided. All 7 feature milestones (M0–M7) are done
      regardless of how this is eventually packaged.

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

## M3: release browsing + grab

`src/models/candidates_model.py` (`CandidatesModel`) — GET `/movies/{id}/candidates` +
POST `/movies/{id}/grab`, stateful (`load(movieId)` remembers which movie subsequent
`grab()` calls act on). `CandidatesPage.qml` — pushed from a new "Find releases" action
on missing library rows in `MoviesPage.qml`, via `applicationWindow().pageStack.push(url,
{movieId, movieTitle})`. The best-scored release gets a purple left-edge accent + a
"best match" `StatusPill`.

**Set up real end-to-end verification for this, not just empty-list happy paths**:
temporarily stopped the systemd `the-den` service, ran a throwaway dev instance of the
current backend code with a real mock indexer (`tests/mock_torznab.py`) and mock
qBittorrent (`tests/mock_qbit.py`) behind it, seeded a real movie, then drove the whole
thing through the client: load real candidates (correct quality/seeders/is_best data),
grab the best one, confirm `grabFinished(true, ...)`. Restored the systemd service
afterward.

**That real-data setup caught a serious, systemic bug that had been shipping silently
in M1 and M2**: `ListView.header` is a `Component`-typed property, so assigning an
inline item to it (as all three pages do, for the search-box-and-status-banner section
above the list) implicitly wraps that item in its own `Component` — which isolates its
`id`s from the rest of the file. Every page had a page-level `Connections` block
*outside* the `ListView` trying to reach a `statusBanner` `id` declared *inside* the
header's implicit Component — invisible from there. `IndexersPage.qml`'s and
`MoviesPage.qml`'s earlier offscreen tests never caught this because neither test ever
actually triggered an error/result signal during its run (M1's test never called
`testIndexer`/`addIndexer`/`deleteIndexer`; M2's never triggered a write failure) — so
the broken `Connections` handler was never actually invoked. **Passing tests were
hiding a real bug because the tests never exercised the code path that used it.**
Separately, `delegate: Kirigami.SwipeListItem { width: listView.width }` (referencing
the containing `ListView`'s own `id` from inside its own delegate) resolved to `null`
specifically when the delegate was for-real instantiated with actual model rows — never
caught either, since no earlier page test had real rows flowing through a `ListView`'s
own direct delegate (M1/M2's `Component.onCompleted` only called `refresh()`, and the
model was always empty at that point in a fresh test DB).

Fixed in all three pages: moved each `Connections` block to be a *sibling of
`statusBanner` inside the header*, not a sibling of the `ListView` outside it. Replaced
every `width: listView.width` in a `ListView`'s own delegate with the attached
`ListView.view.width` property — the Qt-documented, robust way to reference a
containing view from inside its own delegate, which doesn't depend on `id` visibility
at all. For the one delegate that lives inside a `Repeater` inside a `ColumnLayout`
(the search-results list in `MoviesPage.qml`), used `Layout.fillWidth: true` instead of
an explicit width binding, since Repeater items inside a Layout are normal
layout-managed children.

**The lesson, not just the fix**: a headless test that passes only proves the paths it
actually exercised are fine. `Component.onCompleted` calling `refresh()` against an
empty test database is a weak test — it proves the page *loads*, not that it *works*.
From here, every new page's test should seed real data and actually fire every signal
the page listens for (error paths included) before being treated as verified, not just
confirm a clean load with zero rows. Updated `check_indexers_page_qml.py` and
`check_movies_page_qml.py` accordingly (they now trigger `testIndexer`/a duplicate-add
error against real seeded data) alongside the new `check_candidates_model.py` and
`check_candidates_page_qml.py`.

## M4: downloads view

`src/models/downloads_model.py` (`DownloadsModel`) — GET `/downloads`, POST
`/downloads/{id}/check`. `DownloadsPage.qml` — status list with a `StatusPill` per row
(same tone mapping as the web UI: queued/downloading→working, completed→idle,
imported→healthy, failed→warning) and a "Check now" button, hidden once a download is
`imported`.

Applied the M3 lesson from the start this time: `Connections` nested inside the
header's `ColumnLayout` alongside `statusBanner` (not a page-level sibling of the
`ListView`), `ListView.view.width` on the delegate. Both tests seed real data and
actually trigger both the success path (`check()` on a real in-flight download) and the
error path (`check()` on a nonexistent id) before being treated as passing — not just a
clean empty load. Zero new bugs found, which is itself a decent signal the M3 fixes and
the updated testing approach are holding.

Hit real dev-environment friction setting this up, worth remembering: chaining multiple
backgrounded `nohup ... &` process starts across *separate* `wsl -d archlinux -- bash -c
'...'` invocations doesn't reliably keep them alive — put all of them in *one* `bash -c`
invocation (as done successfully throughout this project) or they can silently die when
that particular `wsl.exe` call returns.

## M5: TV library

`src/models/series_model.py` (`SeriesListModel` + `SeriesSearchResultsModel`, mirroring
M2's movie split) and `src/models/episodes_model.py` (`EpisodesModel`, GET
`/series/{id}/episodes`). `SeriesPage.qml` mirrors `MoviesPage.qml`'s search+library
layout. `EpisodesPage.qml` groups episodes by season using `ListView`'s built-in
`section.property`/`section.delegate` + `Kirigami.ListSectionHeader` — a much cleaner
mechanism than the web UI's Jinja `loop.previtem` trick for the same grouping.

**Generalized `CandidatesModel`/`CandidatesPage.qml` for a second real use case**
(episodes), not preemptively: `CandidatesModel` now takes a `resource` ("movies" or
"episodes") since the candidates/grab endpoints are identical except for the URL
prefix. `CandidatesPage.qml`'s `movieId`/`movieTitle` properties became generic
`itemId`/`heading`, plus a `candidatesSource` property (defaults to the movie
`CandidatesModel`, overridable at push time) so both `MoviesPage.qml` and
`EpisodesPage.qml`'s "Find releases" actions push the *same* page, just pointed at a
different model instance. Verified both variants load real, independent data with zero
cross-contamination between the two model instances.

**Two more real findings from applying the M3 testing discipline for real** (not
cosmetic this time, actual test-design bugs caught while writing the tests):
1. `GET /series/{id}/episodes` on the backend doesn't validate the series exists — it
   returns `200 []` for a nonexistent id rather than 404. First draft of
   `check_episodes_page_qml.py` tried to use a bad id as its "error path" trigger and
   silently tested nothing (no error, no exception, just an empty and *plausible-looking*
   result) — caught by actually checking what came back rather than assuming. Fixed
   the test by forcing a genuine network error (pointing the model at an unreachable
   URL) instead. Noted as a known backend gap below, not fixed here.
2. Seeding a pushed page's properties via `root.setProperty()` *after* `engine.load()`
   (the pattern every earlier test used) has a real race: `Component.onCompleted`
   already fires once with the property's *default* value before your `setProperty()`
   call lands, firing a spurious first `load()` whose reply can arrive out of order and
   clobber the real one — this is exactly what happened here, landing on `rowCount: 0`
   after a run that looked otherwise fine. The fix, `engine.setInitialProperties({...})`
   *before* `engine.load()`, is also the more accurate test in the first place: it's
   what `pageStack.push(url, {props})` actually does in the real app, where only one
   `load()` call ever happens. Worth rechecking whether the earlier `check_*_page_qml.py`
   scripts should be updated to this pattern too, even though they haven't shown
   symptoms — `CandidatesModel`'s backend routes happen to 404 on a bad id (unlike
   episodes), which is probably why the same race hasn't bitten those tests yet.

**Known backend gaps found by testing** (not fixed here, noted for the-den):
`GET /series/{id}/episodes` doesn't 404 on a nonexistent series id (see above); plus
the pre-existing `tmdb.search_movie()` 500-on-bad-key gap from M2.

**Latent model-level gap, also not fixed here**: none of this app's `QAbstractListModel`
subclasses guard against out-of-order replies when `load()`/`refresh()` is called twice
in quick succession (no request generation counter to discard a stale reply). Doesn't
affect the current app, since every real navigation only ever calls `load()` once per
page visit — but worth hardening before this matters, e.g. if a future page adds a
manual refresh button someone could double-tap.

## M6: calendar view

There's no JSON `/calendar` endpoint on the backend — only the HTML page. Rather than
grow the backend's API surface for one screen, `src/models/calendar_model.py` composes
it client-side from endpoints that already exist and are already tested:
`CalendarMoviesModel` (GET `/movies`, filtered to `has_file=false`) and
`CalendarEpisodesModel` — the more interesting one, a genuine fan-out/fan-in: GET
`/series` for the list, then one GET `/series/{id}/episodes` per series fired
concurrently, a pending-counter to know when they've all landed, then one combined,
`air_date`-sorted result. `CalendarPage.qml` uses two `Repeater`s in a plain
`ColumnLayout` rather than `ListView`s — no `ListView.header` involved at all here, so
none of the M3 id-scoping bug's precondition even applies to this page by construction.

Verified against real data: a missing movie and 4 missing episodes across 2 seasons
came back correctly aggregated and sorted; forcing a real network error (unreachable
URL, same technique as M5) confirmed the error-handling path works too.

**Testing-process gap found while running the full regression suite this time, worth
fixing eventually**: every `check_*_model.py`/`check_*_page_qml.py` script assumes a
*specific* pre-seeded fixture state (an indexer with id 1, a download already grabbed,
etc.) rather than seeding its own. Running the full suite against a freshly-seeded dev
instance that only had M6's fixtures (a movie, a series) produced several failures that
looked alarming but were just missing fixtures, not regressions — confirmed by
re-seeding the missing pieces and re-running. Fine for now since these are run
individually by hand as each milestone lands, not as automated CI, but if this project
ever gets a CI pipeline these will need to become self-seeding (or share one setup
script) rather than depending on accumulated hand-run `curl` state.

## M7: settings screen

`src/models/settings_controller.py` (`SettingsController`) — a plain `QObject` with Qt
`Property`s (NOTIFY-backed, so QML text fields populate once `load()` returns), not a
`QAbstractListModel`, since this is one record rather than a list. `GET`/`POST
/api/settings` were already built on the backend for exactly this
(the-den's M7-adjacent work). `SettingsPage.qml` is a plain `Kirigami.FormLayout` — no
`ListView` at all here either, same reasoning as `CalendarPage.qml`.

Followed the web UI's settings form exactly on the secret-field handling, since it's a
real correctness-and-security property worth preserving deliberately, not just
incidentally: `GET` never returns a stored secret (TMDB key, qBittorrent password,
Discord webhook), only a `has_*` boolean; a blank field on `save()` means "leave the
stored value alone," not "clear it." Verified this specific behavior for real, not just
assumed it from reading the backend code: saved a real TMDB key, confirmed
`hasTmdbApiKey` flipped true; saved again with that field blank, confirmed it stayed
true (i.e. confirmed the *absence* of a bug — an empty-string save silently wiping a
previously-set secret would be a real, easy-to-make mistake here, and the specific
scenario that would have caught it was deliberately included in the test rather than
assumed away).

## M8: Flatpak packaging — abandoned mid-attempt

Started, hit real friction, then the user called it off. Recording what was actually
tried in case Flatpak comes back up later:

- Installed `flatpak`/`flatpak-builder` and the `org.kde.Platform`/`org.kde.Sdk` 6.10
  runtimes in the WSL Arch environment — this part worked.
- PySide6 isn't bundled in the KDE runtime; it needs to be `pip install`ed as a build
  module. `flatpak-builder`'s build step runs network-isolated by design (only the
  declared "sources" fetch phase gets network, for reproducibility), so this needs
  either the official `flatpak-pip-generator` tool (which pulls in its own Python
  dependency, `python-requirements-parser`, not in the Arch repos) or hand-pinning each
  wheel's exact PyPI URL + sha256 in the manifest.
- Went the hand-pinning route. Hit two points of real friction along the way, both
  solvable but time-consuming: (1) `flatpak run` sandboxes network and arbitrary host
  paths by default — needed `--share=network` and an explicit `--filesystem=` grant,
  and running as `root` (rather than a normal user) caused permission errors inside the
  sandbox that only cleared up switching to a regular user. (2) The downloaded wheels
  (`PySide6-Addons` alone is 167MB) can't be committed to the repo at all — GitHub
  rejects files over 100MB outright — so the only sane approach is pinning upstream
  PyPI URLs + sha256 hashes directly in the manifest (the standard, correct way real
  Flathub manifests do this) rather than vendoring binaries, which was the next step in
  progress when this was called off.
- Nothing was committed to this repo for any of this — all of it lived in the WSL
  scratch environment and one now-removed empty local directory.

Packaging approach is an open question again. Native Arch package (matching how
the-den's own `PKGBUILD` already works, and consistent with this being a HoltOS-only
app) is one obvious alternative worth considering before trying Flatpak again.
