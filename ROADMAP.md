# The Den — Roadmap

One combined Sonarr+Radarr+Prowlarr replacement. Built one milestone at a time,
~1 hour/day. Each milestone must run and be tested before the next starts.

Stack: Python + FastAPI + SQLite (SQLAlchemy/Alembic) + Jinja2/htmx UI.
Deploy target: native systemd service on Arch Linux (no Docker).

## Milestones

- [x] M0 — Skeleton: FastAPI boots, SQLite connects, `/health` works, systemd unit stub
- [x] M1 — Indexer search (Prowlarr core): add Torznab/Newznab indexer, test connection, manual search, ranked results
- [ ] M2 — Movie library (Radarr core): TMDB lookup, add to library, missing/have status
- [ ] M3 — Release scoring: quality profiles + release-title parser, pick best result for a movie
- [ ] M4 — Download + import (movies): send to qBittorrent, monitor, auto-import/rename
- [ ] M5 — TV library (Sonarr core): series/season/episode via TVDB
- [ ] M6 — TV search/grab/import: reuse M3/M4, SxxEyy parsing
- [ ] M7 — Scheduler/RSS automation: background auto-grab on a timer
- [ ] M8 — Notifications + calendar
- [ ] M9 — Distro packaging: systemd unit, config conventions, PKGBUILD

## Notes
- TMDB: free for non-commercial use, attribution required.
- TVDB: needs either a per-user subscription PIN or a free open-source/self-hosted
  license (<$50k revenue, attribution) — same path Sonarr uses. Sort out at M5.
