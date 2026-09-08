# Status

## Last completed
M4: downloads view. `DownloadsModel` + `DownloadsPage.qml` — status list with
`StatusPill` per row, "Check now" (hidden once `imported`). Applied the M3 testing
lesson from the start: real seeded data, both the success and error paths of `check()`
actually triggered and verified, not just a clean empty load. Zero new bugs found this
time. Before that: M3 (release browsing + grab, and the id-scoping bug fix that
affected M1/M2 too — see ROADMAP.md), M2 (movie library), the HoltOS design system,
M0/M1, and repo branding.

## Currently working on
Nothing in progress — M4 is finished, tested for real, committed, and pushed.

## Next steps
- **M5** (next milestone): TV library — series/episodes, mirrors the backend's M5/M6.
- Keep applying the M3 testing lesson: seed real data, trigger every signal a new
  page listens for (not just a clean load) before calling it verified.
- Known backend gap (not yet fixed, belongs in the-den, not here): `app/tmdb.py`'s
  `search_movie()` 500s on an unconfigured/invalid TMDB key instead of a clean error.
- Still no real visual look at the app on an actual screen (no VM/display this
  session). Headless tests now cover network/data correctness quite thoroughly — the
  remaining gap is purely visual/layout polish.
