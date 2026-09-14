# Plan: move the apps to port 40204, then release the-den v0.8.1a (drafted 2026-09-14)

Status: planned, not started. Phase 1 waits on Liam's answer to open question 1.

## Why

M34 (commit 1d72ebc, not tagged) moves the server's default port from 8686 to 40204. The HoltOS
updater appends `WEB_PORT=40204` to `/etc/the-den/the-den.env` when it installs that release, so the
installed server moves to 40204. Liam decided on 2026-09-13 to fix the KDE client and the Android app
first, then release the server as v0.8.1a.

## State on 2026-09-14

- the-den: 8 commits ahead of GitHub (HEAD 9b21d09), PKGBUILD pkgver 0.8.0a.
- the-den-client: 1 commit ahead (c75158f), pkgver 0.5.0a.
- the-den-android: 1 commit ahead (d074e74), versionName 0.7.0, versionCode 22.
- Each repo has a current verified bundle in `/home/liam/Projects/backups`.
- Installed: the-den v0.8.0a on 127.0.0.1:8686, setup complete, no engine errors since boot. The
  updater history line "v0.8.0a (FAILED to start)" came from the updater before the port fix and is stale.
- Down since the reboot: dev backend 8687, KDE fixture backend 8688 with its mocks on 8085 and 8082,
  local swarm 8083, adb.
- Still on 8686: the-den-client `src/api_client.py` line 37 and `src/qml/LoginPage.qml` line 51;
  the-den-android `network/ApiClient.kt` line 22, `ui/screens/LoginScreen.kt` line 68 and
  `LiveBackendTest.kt` lines 27 and 32.
- The installed KDE client and the phones keep their saved 8686 address; a new default does not change it.

## Phase 0: test environment (Claude, shell)

1. Start the dev backend on 8687 and rerun the-den-client `tests/fixture_backend.sh` (8688, 8085, 8082).

## Phase 1: the apps move to 40204

2. KDE client: default and placeholder to `:40204`. If Liam agrees (question 1): when a saved loopback
   `:8686` address fails, try `:40204` and save it if `/health` answers. Profile fast-edit.
3. Android: `DEFAULT_URL` to `http://10.0.2.2:40204`, placeholder and test default to `:40204`;
   versionName 0.7.0a, versionCode 23. Profile trivial.
4. Test: KDE `tests/run_all.sh` against 8688; Android `assembleDebug` and `testDebugUnitTest` against
   8687. Commit each repo and write a bundle.
5. Release the KDE client as v0.5.0b (pkgver 0.5.0b), tag and push, so the fixed client is installed
   before the server moves.

## Phase 2: server v0.8.1a

6. Version 0.8.1a in the PKGBUILD and any other version file; tag v0.8.1a and push.
7. Liam starts the install from the HoltOS Updates window, or the 6-hour timer does.
8. Check: the service listens on 40204, `/health` has `server_id` and `server_name`, the updater
   history shows no failure, and the installed KDE client reconnects.

## Phase 3: cleanup

9. `CONTEXT.txt`: replace the stale "LOCAL MODELS ON THIS MACHINE" section and the Windows repo paths.
   `HANDOFF.md`: point its dev environment section at the Linux notes. `docs/connect-secure-plan.md`:
   the M39 emulator runs under KVM on the Strix Halo, not WSL.
10. the-den-client `tests/qml_harness.py` stops rewriting the tracked `tests/_shell.qml`.

## Phase 4: next milestones (docs/connect-secure-plan.md)

11. M37 device tokens (needs question 4).
12. M35 HTTPS (needs question 3), then M36 UPnP, M38 passkeys, M39 Android, M40 KDE and the M14 shakedown.

## Open questions for Liam

1. Saved 8686 addresses: an automatic fallback to 40204 (recommended), or re-enter them by hand?
2. Phones on the LAN: will Liam set `WEB_HOST=0.0.0.0` in `/etc/the-den/the-den.env` (needs root)
   after v0.8.1a?
3. M35: does anything on the router use external port 80 or 443? From inside the house, does
   `requesthome.asuscomm.com` reach the forwarded port?
4. M37: is signing in enough to add a device, or should an admin approve new devices?

## Decisions

- 2026-09-14: the rules in `~/.claude/CLAUDE.md` apply (Liam pointed to that file). Claude writes
  security-sensitive units itself and takes over a unit whose handoff failed twice; the local models
  write everything else. This replaces the 2026-09-13 note in `CONTEXT.txt` that sent security code to
  the local models.