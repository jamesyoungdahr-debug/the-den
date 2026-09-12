# Plan: indexer presets, native public trackers, Cloudflare solver (M12)

Status: **built 2026-09-12**, see the milestone table at the bottom. Companion to
[requests-plan.md](requests-plan.md) (M11) and the M10 torrent-client notes in
[ROADMAP.md](../ROADMAP.md).

## Why

Until M12 the only way to search was a Torznab/Newznab endpoint, which for public trackers
meant running Jackett or Prowlarr on the side -- the very thing The Den exists to replace.
Prowlarr's answer is a catalog of per-site definitions the user picks from, adding only
credentials where a site needs them. M12 gives The Den the same shape without a
definition language: a catalog of presets, native Python implementations for the public
trackers that have no Torznab API, and a Cloudflare solver for the sites that hide behind
one.

## What was built

### Catalog (`app/indexers/catalog.py`, `GET /indexers/presets`)

26 presets in three kinds:

| Kind | Entries | Credentials |
|---|---|---|
| public | Knaben, The Pirate Bay, YTS, Nyaa, LimeTorrents, TorrentDownloads, EZTV, 1337x, AnimeTosho | none |
| usenet (Newznab) | NZBgeek, NZBFinder, DrunkenSlug, NZBPlanet, nzb.su, DOGnzb, NZBCat, altHUB, NinjaCentral, Tabula Rasa, abNZB, NZBNDX, Usenet Crawler | API key |
| generic | Jackett, Prowlarr, Custom Torznab, Custom Newznab | URL (+ API key) |

Each preset says which form fields to show (`fields`), whether it needs an API key, and
whether it sits behind Cloudflare. `POST /indexers` accepts `preset` (the slug) and fills
name, URL and implementation from the catalog when they are omitted, so a client can add a
public tracker with a single field.

### Native implementations (`app/indexers/native.py`)

One small class per tracker, all returning the same `Release` records the Torznab client
does, so scoring, grabbing and every page are unchanged:

- Knaben (JSON meta-search over dozens of trackers; recommended first indexer), The Pirate
  Bay (apibay JSON), YTS (JSON), Nyaa / LimeTorrents / TorrentDownloads (RSS), EZTV and
  1337x (HTML, both behind Cloudflare).
- Magnets are built from info-hashes where a site only exposes those, with a fixed list of
  open trackers appended so the engine finds peers quickly.
- `_rss()` cuts everything after `</rss>`: Cloudflare appends a `<script>` to some feeds,
  which the XML parser otherwise rejects as "junk after document element".

`app/indexers/__init__.py` is the single dispatch point (`search_all`, `test_one`): the
candidates search, the manual search API and the web indexers page all go through it, and
every enabled indexer is searched concurrently with a failing one skipped.

### Cloudflare solver (`app/indexers/fetch.py`, `app/indexers/solver.py`)

- `Fetcher` does plain HTTP, recognises a Cloudflare challenge (403/503 with the challenge
  markers, or the `cf-mitigated` header) and re-fetches through a solver.
- **External** FlareSolverr or Byparr (same `/v1` API): URL in Settings → Indexers,
  `POST /indexers/solver/test` checks it.
- **Built-in**: `nodriver` drives the system Chromium (the PKGBUILD depends on
  `chromium`; `CHROME_BIN` overrides), waits out the passive challenge and clicks the
  Turnstile checkbox when one appears. Headed when `DISPLAY` is set, Chromium's new headless
  mode otherwise. `nodriver==0.46` is pinned: 0.47+ ship a generated file Python 3.14
  refuses to import, and 0.46's own `headless=True` path recurses forever, hence
  `headless=False` plus the `--headless=new` flag.
- A settings field `flaresolverr_url` (DB column, env `FLARESOLVERR_URL`) on the web
  settings page, `/api/settings`, the Android app and the KDE client.

### Clients

- Web: the add-indexer dialog is a grouped preset picker that prefills the form and only
  shows the API-key field when the preset needs it; rows show the implementation.
- Android: the same picker as chips in the add sheet, plus the solver URL in Settings.
- KDE client: `IndexerListModel.presets` / `loadPresets()` / `addIndexer(preset, ...)`,
  the dialog's preset combo, and the solver URL on the settings page.

## Verified

- Live from the dev machine: Knaben (100 results), The Pirate Bay (100), Nyaa (75),
  LimeTorrents (40), TorrentDownloads (50) all pass the connection test and a combined
  manual search returned 201 releases.
- Offline parser checks for every native implementation and the helpers:
  `python tests/test_native_indexers.py` (11 checks). Drafted by the local model from
  recorded sample responses.
- KDE client: `tests/check_indexer_model.py` (add/test/delete round trip) and a preset
  load through the model, both against the dev backend. The QML pages await the
  real-desktop pass.
- Migration `c9d0e1f2a3b4` (`indexers.implementation`, `indexers.preset`,
  `settings.flaresolverr_url`) applied on a fresh and an existing database.

## Not verified, and why

- **YTS**: the dev network's DNS blocks `yts.mx`; the preset text tells the user to try a
  mirror URL. The parser is covered offline.
- **1337x and EZTV through the built-in solver**: Cloudflare never cleared the challenge
  from the dev network, with stock Chrome, headed on a virtual display, as a non-root
  user, and the in-app browser on the same network shows the same endless spinner. That
  is the network's reputation, not the automation. Needs the real HoltOS box on a
  residential connection; until then the built-in solver is best-effort and the external
  FlareSolverr/Byparr path is the documented fallback.

## Decisions

- No Cardigann-style definition language. Eight hand-written implementations cover the
  public trackers people actually use; adding one is a 20-line class, and the offline test
  pins its format.
- Chromium is a package dependency rather than an optional extra, so the built-in solver
  works out of the box on HoltOS. Machines without it fall back to the external URL or a
  clear error naming both options.
- Presets are data on the server, not in the clients: all three clients render the same
  list from `GET /indexers/presets`, so a new tracker needs no client release.

## Milestones

| Step | Status |
|---|---|
| M12a catalog + `POST /indexers` from preset + web picker | done 2026-09-12 |
| M12b native public trackers + dispatch + offline tests | done 2026-09-12 |
| M12c Cloudflare: external FlareSolverr/Byparr + built-in Chromium solver | done 2026-09-12, built-in solver unverified against a live challenge (see above) |
| M12d Android + KDE pickers and solver field | done 2026-09-12 (KDE QML pending the real-desktop pass) |
