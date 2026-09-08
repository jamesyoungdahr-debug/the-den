# Status

## Last completed
M3: release browsing + grab. `CandidatesModel` + `CandidatesPage.qml`, reachable via a
new "Find releases" action on missing movies. Set up real end-to-end verification
(temporary dev backend + mock indexer + mock qBittorrent, not just empty-list tests) —
which caught a serious pre-existing bug in **all three** pages (M1 and M2 included):
`ListView.header`'s implicit `Component` wrapping isolated `statusBanner`'s `id` from
the page-level `Connections` blocks trying to reach it, and `delegate: { width:
listView.width }` resolved to `null` once real rows actually instantiated a delegate.
Neither had ever been exercised by the earlier "loads with zero rows" tests. Fixed in
all three pages; full story and the testing lesson are in ROADMAP.md's "M3" section —
worth reading before writing the next page's test.

Before that: M2 (movie library), the HoltOS design system applied, M0/M1. Also
repo-branded on GitHub (description, topics, logo, README header).

## Currently working on
Nothing in progress — M3 is finished, tested for real (not just headlessly against an
empty DB), committed, and pushed.

## Next steps
- **M4** (next milestone): downloads view — status list, manual "check now". Mirrors
  the backend's `/downloads` + `/downloads/{id}/check`.
- **Apply the M3 testing lesson going forward**: any new page's test must seed real
  data and actually fire every signal the page listens for, not just confirm a clean
  load with zero rows. A passing test that never exercised a code path proves nothing
  about that path.
- Known backend gap (not yet fixed, belongs in the-den): `app/tmdb.py`'s
  `search_movie()` 500s on an unconfigured/invalid TMDB key instead of a clean error.
- Still no real visual look at the app on an actual screen (no VM/display this
  session). Headless tests now confirm real network/data correctness quite thoroughly
  (see above) — the remaining gap is purely visual/layout polish.
