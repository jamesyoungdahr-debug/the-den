# The Den — Roadmap

One combined Sonarr+Radarr+Prowlarr replacement. Built one milestone at a time,
~1 hour/day. Each milestone must run and be tested before the next starts.

Stack: Python + FastAPI + SQLite (SQLAlchemy/Alembic) + Jinja2/htmx UI.
Deploy target: native systemd service on Arch Linux (no Docker).

## Milestones

- [x] M0 — Skeleton: FastAPI boots, SQLite connects, `/health` works, systemd unit stub
- [x] M1 — Indexer search (Prowlarr core): add Torznab/Newznab indexer, test connection, manual search, ranked results
- [x] M2 — Movie library (Radarr core): TMDB lookup, add to library, missing/have status
- [x] M3 — Release scoring: quality profiles + release-title parser, pick best result for a movie
- [x] M4 — Download + import (movies): send to qBittorrent, monitor, auto-import/rename
- [x] M5 — TV library (Sonarr core): series/season/episode via TMDB (not TVDB, see notes)
- [x] M6 — TV search/grab/import: reuse M3/M4, SxxEyy in the search query
- [x] M7 — Scheduler/RSS automation: background auto-grab on a timer
- [x] M8 — Notifications + calendar
- [x] M9 — Distro packaging: systemd unit, config conventions, PKGBUILD

## Notes
- TMDB: free for non-commercial use, attribution required.
- Decided against TheTVDB for M5: TMDB's `/tv` endpoints give full series/season/episode
  data for free too, so one metadata provider covers both movies and TV — no second API
  key, no TVDB per-user-PIN/licensing question to deal with.
- Real config goes in `.env` (see `.env.example`): TMDB_API_KEY, QBIT_URL/USERNAME/PASSWORD,
  MOVIES_ROOT, TV_ROOT. Until you set a real TMDB key/qBittorrent, `tests/mock_tmdb.py`,
  `tests/mock_qbit.py`, and `tests/mock_torznab.py` let the whole app be tested
  end-to-end without live accounts.
- Download tracking uses qBittorrent categories (`the-den-movie-<id>` /
  `the-den-episode-<id>`), not info-hash, since the add API doesn't return one synchronously.
- Known simplification: episode search doesn't verify the grabbed release's season/episode
  actually matches (relies on the SxxEyy search query steering indexer results correctly).
  Fine for now; a stricter release-title parser could validate this later if it causes
  wrong grabs in practice.
- No authentication anywhere in the app. Fine on localhost/behind a VPN; do not expose
  it directly to the internet without adding one (or fronting it with an auth-checking
  reverse proxy).
- M9 packaging (PKGBUILD, systemd, sysusers/tmpfiles) is written to real Arch conventions
  but was authored on a Windows dev machine — it has not been through an actual
  `makepkg -si` + `pacman -U` cycle. Test it for real on the distro before trusting it.

## All milestones done — what's next is real-world shakedown, not new code

The build is feature-complete per this roadmap. What's left is exercising it against
real accounts/services (see README) and fixing whatever that surfaces — that's expected
to turn up rough edges no amount of mock-based testing catches.
