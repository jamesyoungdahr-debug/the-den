# Status

## Last completed
Fixed 8 correctness bugs found by a full-codebase review (commit `c2a6da4`):
orphaned `DownloadRecord`s after a movie/series delete crashing automation forever,
`/ui/settings` crashing on `scheduler.reschedule()` under conditions `/api/settings`
already guarded against, a race on duplicate `tmdb_id`/`tvmaze_id` inserts producing
a 500 instead of 400, `torznab` crashing on a valueless `<attr>` tag, series creation
partial-committing before the TVMaze episode fetch (leaving an unrecoverable stuck
row on failure), qBittorrent login failures going undetected (its API returns 200
even on bad credentials), `episode_candidates` crashing on a series deleted
mid-request, and an explicit `automation_interval_seconds=0` being silently
discarded instead of rejected. All 8 verified live against the running WSL
instance — see the session transcript for the exact repro/verification per bug.
Before that: added `GET`/`POST /api/settings` (JSON) — needed by the-den-client's
future M7.

## Currently working on
Nothing in progress. The review-fix pass is committed and pushed.

## Next steps
- **Real-world shakedown** (the one thing never actually done): a real TMDB API key,
  a real indexer account, real qBittorrent running — add a real movie and watch it
  really download. Everything so far has only been tested against mocks or the
  packaging shakedown.
- The review that produced the fixes above also surfaced a well-corroborated set of
  **cleanup/duplication findings**, deliberately left unfixed (correctness came
  first): the same query-building + quality-profile-fallback logic duplicated 6x
  across `movies.py`/`series.py`/`ui.py`/`automation.py`; the same grab-error-wrapping
  duplicated 6x; `grab_movie`/`grab_episode` and `import_movie`/`import_episode`
  near-identical pairs; N+1 queries in `ui.py`'s `calendar()` and `tv_library()`;
  `scheduler.py`'s module-level global instead of DI. Worth a dedicated pass later.
- Optional: wire up real poster art (tiles currently show the intentional striped
  placeholder — TMDB/TVmaze poster URLs aren't fetched/displayed yet).
