# Status

## Last completed
Fixed 2 correctness bugs found by a full-codebase review (commit `d157416`), both
the same root cause: `CandidatesModel` and `ApiClient` are shared singleton
instances with no guard against a slow, superseded network reply landing after a
newer one. `CandidatesModel` could show a slow grab's result on whatever movie's
page the user had since navigated to, and could overwrite the currently-open
page's release list with a different movie's data if its `load()` reply arrived
late; `ApiClient.checkHealth()` could show a stale "Connection failed" over a
newer, correct "Connected". Both fixed with a local request-sequence counter, not
a project-wide model refactor. New isolated tests
(`tests/check_candidates_model_race_guard.py`,
`tests/check_api_client_race_guard.py`) exercise both races against a fake
backend and pass; `tests/check_candidates_model.py` updated for
`grabFinished`'s new 3-arg signature (untested this pass — needs real mock
indexer/qBittorrent fixtures that weren't set up).

Before that: M8 (take two, after Flatpak was abandoned) — native Arch package.
All 7 feature milestones (M0–M7) plus packaging are done.

## Currently working on
Nothing in progress. The review-fix pass is committed and pushed.

## Next steps
- **Get a real look at it.** The one thing left that this dev environment genuinely
  cannot provide: install the package (or just `makepkg -si` from this repo) on the
  actual HoltOS target hardware/VM and see it run for real — spacing, layout, does it
  actually look like the design intent.
- Known backend gaps (not fixed here, belong in the-den): `tmdb.search_movie()` 500s
  on a bad key; `GET /series/{id}/episodes` doesn't 404 on a nonexistent series id.
- Known client-side gap, now **partially** addressed: `CandidatesModel` and
  `ApiClient` have the out-of-order-reply guard as of the fixes above; every other
  `QAbstractListModel` subclass (`MovieListModel`, `SeriesListModel`,
  `EpisodesModel`, `DownloadsModel`, `IndexerModel`, `CalendarEpisodesModel`, the
  `*SearchResultsModel` pair) still doesn't have it — deliberately out of scope for
  the review-fix pass, which targeted the two confirmed concrete failure scenarios
  rather than a project-wide model refactor.
- The review also flagged real duplication worth a dedicated pass: the movie/series
  model pairs (`MovieListModel`/`SeriesListModel`,
  `MovieSearchResultsModel`/`SeriesSearchResultsModel`) are near-identical and could
  share a base class; the same error-banner `Connections`+`InlineMessage` QML
  boilerplate is copy-pasted across all 7 pages; `CalendarEpisodesModel` re-fetches
  data `MovieListModel`/`EpisodesModel` already hold instead of deriving from it.
- Known testing-process gap: regression scripts assume shared pre-seeded fixtures
  rather than self-seeding (see M6 in ROADMAP.md).
- If Flatpak distribution is wanted later too (e.g. for non-HoltOS use), the M8
  attempt notes in ROADMAP.md capture exactly where that got stuck and why.
