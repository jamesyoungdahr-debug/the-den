# Status

## Last completed
Redesigned all 8 web UI pages to the HoltOS design system (`app/static/den.css`,
`app/templates/base.html`, full `design/` source copied into the repo). Before that:
all planned milestones M0–M9 complete, plus TVmaze (no-account TV metadata) and an
in-app Settings page. Arch packaging verified for real via `makepkg`/`pacman`/`systemctl`
on WSL2 Arch.

## Currently working on
Nothing in progress — the redesign was the last task and it's finished, tested in the
browser against seeded data, committed, and pushed.

## Next steps
- **Real-world shakedown** (the one thing never actually done): a real TMDB API key,
  a real indexer account, real qBittorrent running — add a real movie and watch it
  really download. Everything so far has only been tested against mocks or the
  packaging shakedown.
- Optional: wire up real poster art (tiles currently show the intentional striped
  placeholder — TMDB/TVmaze poster URLs aren't fetched/displayed yet).
- Needed eventually for the-den-client's M7: a JSON API for settings (currently
  `/ui/settings` is HTML-form-only).
