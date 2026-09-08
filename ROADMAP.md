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
- Movies: TMDB. Free for non-commercial use, attribution required, needs a free API key
  (2-minute signup at themoviedb.org).
- TV: switched from TMDB to **TVmaze** (`app/tvmaze.py`) — free, no API key, no account
  at all. `Series.tvmaze_id` is a TVmaze show id, unrelated to TMDB's id space; `Movie`
  still uses `tmdb_id`. Originally used TMDB's `/tv` endpoints for M5 (see commit
  history) to avoid TheTVDB's licensing question entirely, but TVmaze removes even the
  TMDB signup for the TV half of the app, so switched over.
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
- M9 packaging (PKGBUILD, systemd, sysusers/tmpfiles) has been verified for real: a
  genuine Arch Linux environment (WSL2, systemd enabled), full `makepkg -si` +
  `pacman -U` + `systemctl enable --now`, service came up and answered `/health`.
  Found and fixed one real bug this way: the post-install migration failed with
  `ModuleNotFoundError: No module named 'app'` because `runuser` doesn't `cd` into
  `/opt/the-den` on its own, so alembic's `env.py` (which does `from app.db import
  Base`) couldn't find the package. Also disabled makepkg's debug-package generation
  — meaningless for pure Python and it chokes on Python 3.14 venv's new `𝜋thon`
  symlink easter egg. Not literally CachyOS (its kernel/scheduler differences don't
  come into play under a shared-kernel WSL environment), but identical at the
  pacman/systemd level that this packaging actually touches.

## Post-M9 addition: in-app Settings page

Added a `settings` DB table + `/ui/settings` page so TMDB key, qBittorrent connection,
library folders, automation interval, and the Discord webhook can all be set from the
browser instead of hand-editing `.env`/the systemd env file. `app/settings.py`'s
`effective(db)` layers DB overrides on top of `app/config.py`'s env-var defaults — env
vars still work (useful for the Arch packaging's `/etc/the-den/the-den.env`), the UI
just wins when both are set. Secret fields (TMDB key, qBit password, Discord webhook)
never echo their stored value back into the page; leaving them blank on save keeps the
existing value. Changing the automation interval reschedules the running APScheduler
job immediately via `scheduler.reschedule()`, no restart needed.

## All milestones done — what's next is real-world shakedown, not new code

The build is feature-complete per this roadmap. What's left is exercising it against
real accounts/services (see README) and fixing whatever that surfaces — that's expected
to turn up rough edges no amount of mock-based testing catches.
