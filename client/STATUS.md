# Status

## Last completed
**U4 -- the HoltOS Glass redesign of the whole client (2026-09-12).** Everything was
rebuilt on the backend's current API:

- **Sign-in.** Login page with *Sign in with Plex* (backend PIN flow, plex.tv opens in
  the system browser, the client polls) and a local username/password form; either way
  the client swaps the session for a personal API token (`POST /api/auth/token`), keeps
  only that in QSettings, and sends it as `X-Api-Key`. `GET /api/auth/me` decides what
  the shell shows (admin group, request buttons, quota).
- **Shell.** Glass sidebar with Browse / Library / Admin groups (Admin only for admins,
  pending-requests badge), rail mode when collapsed or under 900px, top bar with global
  search and the page's single primary action, page stack, toasts.
- **Pages.** Discover (hero + Recommended for you + rails), Search (poster grid with type
  chips), Detail (backdrop hero, facts, genres, cast, seasons with per-season
  availability, availability panel, request/add with a season picker, recommendations),
  Requests (filters, approve / decline with a note / withdraw / remove), Movies and TV as
  poster grids with add dialogs, Episodes with progress and per-season sections,
  Releases with quality chips and best-match, Calendar as an agenda (missing / upcoming /
  movies wanted), Downloads on `/torrents` (engine header, grouped rows with drawn
  progress bars, pause / resume / remove, add by hand, polling while visible), Indexers
  with test/delete and an add dialog, Settings as cards bound to `/api/settings` (fixed:
  it had been broken since the torrent client replaced qBittorrent).
- **Code.** `JsonListModel`/`JsonRecord` base (fields declared, roles generated, the
  reply-sequence guard everywhere, `loading`/`count`), so the near-identical model pairs
  and the copy-pasted error banner block flagged by the last review are gone. `theme.py`
  reads the shared `design/exports/holt_tokens.py`. A `holt/` QML component library.
- **Verified headlessly** against the dev backend: 10 model checks, the page compile
  harness (13 pages, zero QML warnings) and a full-app screenshot walk (10 PNGs, zero
  warnings) via `tests/run_all.sh`. Two PySide pitfalls found on the way and documented
  in the code: a `Property` notify must be a signal declared on the same class (a base
  signal, or re-declaring the base's name, segfaults), and integer `font.pixelSize`.

## Currently working on
Nothing in progress; U4 is committed.

## Next steps
- **See it on a real screen.** The screenshot walk uses the Basic QQC2 style offscreen;
  `org.kde.desktop` on the HoltOS desktop may size controls differently. Run
  `makepkg -si` from the repo root there (the client ships inside the `the-den` package) and click through.
- Live blur behind the sidebar/top bar (`MultiEffect`) once seen on real hardware; the
  ground-layer glass is deliberate for now.
- Users page (per-person quotas, roles) is web-only; the client points there.
- Window state (size, sidebar collapsed) is not yet remembered between runs.
