# Status

## Last completed
Applied the HoltOS design system to the app (`src/theme.py`, `Kirigami.Theme` cascade
override in `Main.qml`, `RingMark`/`StatusPill` components). M0 (connect to backend) and
M1 (indexers: list/add/delete/test) are done, tested headlessly, committed, and pushed.

## Currently working on
Nothing in progress — the design pass was the last task and it's finished and pushed.

## Next steps
- **M2** (next milestone per `ROADMAP.md`): movie library — TMDB search, add, missing/have status.
- Still no real visual look at the app on an actual screen (no VM/display available
  this session; WSLg screenshot access was inconclusive). Headless tests confirm it
  compiles and the theme resolves correctly, not that it looks right on screen.
- Later: M3–M7 (releases/grab, downloads, TV, calendar, settings), M8 (Flatpak
  packaging via `org.kde.Platform`, actually built and run).
