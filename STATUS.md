# Status

## Last completed
**M10 -- built-in torrent client.** The external qBittorrent dependency is gone; The Den
now embeds libtorrent-rasterbar (`app/torrent/engine.py`) and downloads releases itself.
Grabs go straight into the in-process session, the importer hard-links finished files into
the library so torrents keep seeding, seed ratio/time limits stop them, and the automation
cycle reaps stopped+imported torrents with their data. New `/torrents` JSON API and a live
Downloads page (progress, rates, peers, ETA, pause/resume/remove, add-by-hand). Settings
gained a "Torrent client" section (downloads folder, port, rate limits, seed limits);
`qbit_*` settings and `DownloadRecord.category` were removed by migration `b7e2f1c4d9a0`.

Verified end to end against `tests/local_swarm.py` (a private seeder + tracker on
localhost): grab → real download → import (same inode as the seeding copy) → `has_file`
→ seed-time limit → reaped; manual magnet add via 302 redirect; pause/resume; restart
restores torrents from resume data. See ROADMAP.md's M10 section for the details and the
two loopback-swarm gotchas that cost the most debugging time.

## Currently working on
**UI redesign U0 is done** (`design/tokens.json`, `design/build_tokens.py`,
`design/docs/glass-components.md`; see `docs/ui-redesign-plan.md`). **Next is U1, the web
shell.** Also planned: M11 Discover + Requests -- design,
milestones and open decisions are in `docs/requests-plan.md`. Also planned: a full UI redesign
("HoltOS Glass", `docs/ui-redesign-plan.md`) whose shell/component work comes before M11's pages. Not started.

## Next steps
- **Real-world shakedown** (still the one thing never done): a real TMDB key, a real
  indexer. The engine itself HAS now been run against a public swarm: the Ubuntu 24.04.4
  ISO torrent pulled 60+ peers via tracker+DHT and peaked at 45 MiB/s, with the rate
  limiter and live settings reload both confirmed. Still untested: a real indexer grab.
- **the-den-client / the-den-android need updating** (reviewed; see `docs/requests-plan.md`
  "Companion apps" -- the Android Settings screen is actually broken by this): `GET/POST /api/settings` no longer
  has `qbit_url` / `qbit_username` / `qbit_password` / `has_qbit_password`; it has
  `downloads_root`, `state_dir` (read-only), `torrent_port`, `download_rate_limit_kib`,
  `upload_rate_limit_kib`, `seed_ratio_limit`, `seed_time_limit_minutes` instead. They can
  also now use `/torrents` for live download progress.
- Torrent client polish worth doing once real use shows the need: per-torrent file
  selection, sequential download, IP filter, proxy support, a session-wide stats line
  (libtorrent exposes all of these; none are wired yet).
- Cleanup findings from the earlier code review still stand: the same query-building +
  quality-profile-fallback logic duplicated across `movies.py`/`series.py`/`ui.py`/
  `automation.py`; N+1 queries in `ui.py`'s `calendar()` and `tv_library()`;
  `scheduler.py` (and now `app/torrent/engine.py`) using a module-level global instead of DI.
- Optional: wire up real poster art (tiles currently show the intentional striped
  placeholder -- TMDB/TVmaze poster URLs aren't fetched/displayed yet).
