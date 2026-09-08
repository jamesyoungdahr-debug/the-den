# Status

## Last completed
M2: movie library. `src/models/movie_model.py` (`MovieListModel` + `MovieSearchResultsModel`)
and `MoviesPage.qml` — search TMDB, add to library, missing/have status via `StatusPill`.
Verified headlessly against the real backend: add/list/delete round-trip correctly;
search error handling works (surfaces via `errorOccurred`, doesn't crash — see below).
Before that: the HoltOS design system applied (M0/M1 restyled), M0 (connect) and M1
(indexers) done.

Also cleaned up before starting: a previous, non-memory-having attempt at M2 left
`src/models/movie_model.py` as an actual empty directory (not a file) and a `context/`
folder of fabricated docs claiming false progress. Deleted; real M2 work started clean
from `master`. Full story in ROADMAP.md's "M2: movie library" section.

## Currently working on
Nothing in progress — M2 is finished, tested, committed, and pushed.

## Next steps
- **M3** (next milestone): release browsing + grab — view scored candidates for a
  movie, grab the best/a chosen one. Mirrors the backend's `/movies/{id}/candidates`
  and `/movies/{id}/grab`.
- Known backend gap found via M2 testing, not yet fixed (belongs in the-den, not
  here): `app/tmdb.py`'s `search_movie()` lets `resp.raise_for_status()` bubble up
  uncaught, so an unconfigured/invalid TMDB key produces a raw 500 instead of a clean
  error. The client already handles this gracefully either way, but a nicer backend
  error would let it show a better message.
- Still no real visual look at the app on an actual screen (no VM/display this
  session). Headless tests confirm compile-correctness and network-correctness, not
  on-screen layout.
