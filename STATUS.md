# Status

## Last completed
Added `GET`/`POST /api/settings` (JSON, alongside the existing `/ui/settings` HTML
form) — needed by the-den-client's future M7. Verified live: secrets never echoed,
`has_*` flags flip correctly, changes persist. Before that: redesigned all 8 web UI
pages to the HoltOS design system, and before that all planned milestones M0–M9 plus
TVmaze and the in-app Settings page. Arch packaging verified for real via
`makepkg`/`pacman`/`systemctl` on WSL2 Arch.

## Currently working on
Nothing in progress — the JSON settings API was the last task, tested, committed, and
pushed.

## Next steps
- **Real-world shakedown** (the one thing never actually done): a real TMDB API key,
  a real indexer account, real qBittorrent running — add a real movie and watch it
  really download. Everything so far has only been tested against mocks or the
  packaging shakedown.
- Optional: wire up real poster art (tiles currently show the intentional striped
  placeholder — TMDB/TVmaze poster URLs aren't fetched/displayed yet).
