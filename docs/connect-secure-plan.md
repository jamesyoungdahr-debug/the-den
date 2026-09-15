# Plan: sign-in, HTTPS, passkeys, discovery and remote access (M33 to M40), then the Tier 3 queue (drafted 2026-09-13)

Turns Liam's 2026-09-13 requests into milestones, in dependency order. Same rules as every
milestone so far: one at a time, each verified against a running backend before the next
starts, each ends with the client work so the KDE and Android apps never fall behind.

Who writes what: the security-sensitive units (sign-in and setup gates, TLS and certificates,
the remote-access guard, passkeys, device tokens, certificate pinning) are written by Claude
directly, under the standing exception for auth and security logic. Everything else (UI,
templates, wiring, docs) goes to the local models from exact specs, and Claude reviews every diff.

Commits (Liam, 2026-09-13): each milestone is committed locally once it is verified, and nothing
is pushed until Liam says so. Because unpushed work was lost once before (the rm -rf incident in
CONTEXT.txt), Claude writes a git bundle of each repo outside the working trees after every commit.

## What was asked

- Sign-in is always required, and a first-run setup has to be finished before the server
  will talk to any app or client.
- The server opens its own port on the router with UPnP so the apps work away from home.
- The KDE client and the Android app find servers on the LAN or WLAN by themselves (never
  over mobile data) and list them: the Plex server's name when the server is tied to Plex,
  otherwise the name of the machine it runs on.
- The apps remember a server, its remote address included, and use whichever address works.
- Remote reachability uses the existing DDNS name `requesthome.asuscomm.com` now, and
  Cloudflare DNS later.
- HTTPS.
- Passkeys, including for users who signed in with Plex: their account gets a unique
  identifier so they can also sign in with a passkey.
- Then the Tier 3 short list: per-title pickers, usenet on Downloads, the README scope note,
  W2, W8, W9, W6, W5 and W3.

## Decisions taken (override any of these before M33 starts)

| Decision | Default | Why |
|---|---|---|
| Sign-in | **Always on.** The anonymous-admin mode and the `AUTH_REQUIRED` switch go away. Until setup is finished, every route except `/health`, the setup pages and static files answers 503 "setup required". | A server reachable from the internet can't have an anonymous admin. |
| Public name | **A pluggable "public address" setting.** First provider: *router DDNS* (`requesthome.asuscomm.com`; the ASUS router keeps it pointed at the home IP, the server only needs the name). Later provider: *Cloudflare* (zone, record and a scoped API token; the server updates the record itself). | Moving to Cloudflare becomes a settings change, not a rewrite. |
| Certificates | **Self-signed now, pinned by the apps; Let's Encrypt only through DNS-01 later.** Liam, 2026-09-14: ports 80 and 443 are never used, so HTTP-01 and TLS-ALPN-01 are out, and the router DDNS name has no DNS API for DNS-01. M35 generates a self-signed certificate for the public name, the LAN addresses and the hostname; the apps pin its public key (`sha256/<base64>` of the SubjectPublicKeyInfo, OkHttp's format) at first sign-in, tied to the server id, and Settings shows the pin. A certificate browsers trust arrives with the Cloudflare provider (M48, DNS-01 through the Cloudflare API, no inbound port). | The only ACME challenge that needs no port 80 or 443 is DNS-01, which needs a DNS provider with an API. |
| LAN traffic | **HTTPS as well.** An app that reaches the server by LAN IP checks the certificate against the public name and pins its fingerprint, learned at first sign-in and tied to the server id. Plain HTTP stays on loopback only, for local tools. | No password or token ever crosses a network in clear text. |
| Remote access | **Off until HTTPS works.** The UPnP mapping refuses to turn on without a valid certificate, and switches itself off if the certificate stops being valid. | Never expose plain HTTP. |
| Discovery | **mDNS / DNS-SD, service `_theden._tcp`,** TXT records `name`, `id`, `api` and `https` (port). Server and KDE: `zeroconf`. Android: `NsdManager`, only while on Wi-Fi or Ethernet. | Standard, link-local by design, no home-made broadcast protocol. |
| Server identity | A random server id kept under `STATE_DIR`. Display name: the Plex server's name when Plex is connected, else `SERVER_NAME`, else the hostname. | Lets the apps match a LAN address and a public address to one server. |
| Port | **40204**, both where the server listens (`WEB_PORT`) and the public port the router forwards, so the public address is `https://requesthome.asuscomm.com:40204`. The apps' default addresses change to it. The dev backend on this PC stays on 8686 until Liam moves the Windows port forward. | Liam's choice, 2026-09-13. |
| App tokens | **One named token per device**, created at sign-in, listed and revocable on the profile page, replacing the single per-user API token. | Losing a phone shouldn't mean resetting every app. |
| Passkeys | **WebAuthn via `webauthn` (py_webauthn 3.0.0).** Relying party: the public name. Every user gets a random WebAuthn user handle, Plex-linked users included, and can register several passkeys. Web: the browser API. Android: Credential Manager, with `/.well-known/assetlinks.json` served by the server. KDE: the system browser does the passkey step and hands a token back, the way Plex sign-in already works. **Moved after M48 (2026-09-14):** browsers refuse WebAuthn on a certificate they don't trust, and Android fetches assetlinks only over trusted HTTPS, so M38 waits for the Cloudflare certificate. | Passkeys need a domain and a certificate browsers trust. |

## Open questions for Liam (answer before the milestone that needs it)

1. **Router ports (M35). ANSWERED 2026-09-14: never use 80 or 443.** Does anything on the ASUS router already use external port 80 or
   443 on `requesthome.asuscomm.com` (remote web admin, the router's own Let's Encrypt)?
   HTTP-01 needs port 80 while issuing and renewing. If the router holds it, either move the
   router's remote admin to another port or wait for Cloudflare DNS-01.
2. **Public port (M36).** Decided: 40204 (see the Port row above).
3. **NAT loopback (M39, M40). ANSWERED 2026-09-14: unknown, so the server finds out itself (M36).** From inside the house, does `requesthome.asuscomm.com` reach
   the forwarded port? If not, the apps use the LAN IP with pinning (planned anyway), and web
   passkeys only work away from home or with a local DNS override.
4. **Device approval (M37).** Is signing in enough to add a device, or should an admin approve
   new devices first? Default: signing in is enough; admins can revoke.
5. **Existing installs (M33).** An install running without accounts is sent to the setup page
   on its first start after the upgrade. OK?

## Milestones

### M33 Always sign in, first-run setup (server, web, KDE, Android) -- server 0.8.0

- Remove the anonymous admin: sign-in is always required; `AUTH_REQUIRED`, the Settings >
  Accounts switch and the stored override go away. Anonymous requests get 401 (API) or the
  login page (web).
- Setup gate: until setup is complete, every route except `/health`, `/setup*` and static
  files answers 503 with `{"detail": "setup required"}`. `/health` gains `setup_complete`.
- Setup wizard on the web: admin account (password or Plex), server display name, library
  folders. M35 and M36 add HTTPS and remote-access steps.
- Clients: remove "Continue without signing in"; show "Finish setup in the web UI" when
  `setup_complete` is false.
- Test fixtures stop using `AUTH_REQUIRED=false`: the e2e scripts and Android's
  `LiveBackendTest` use a seeded admin and token.
- Verify: on a fresh DB every API route answers 503 until setup; after setup, anonymous
  requests get 401 everywhere; e2e with tokens; KDE harness; Android build and tests.

### M34 Server identity and LAN discovery (server) -- DONE 2026-09-13, not released yet

Status: done and verified on 2026-09-13 (details in STATUS.md). Two choices differ from the bullets below.
The unit runs `python -m app`, which reads `WEB_HOST` and `WEB_PORT` itself, so an env file without those
keys still starts, on 127.0.0.1:40204. The TXT record carries `name`, `id` and `api`; `https` is added in M35.

- `config.WEB_HOST`, `WEB_PORT` and `SERVER_NAME` (drafted by the local model, uncommitted);
  the systemd unit passes them to uvicorn; README and the env example explain LAN binding.
- `app/discovery.py` (drafted by the local model, uncommitted, not yet reviewed): server id,
  display name, the `_theden._tcp` advertisement, and a re-announce when the Plex server or
  the name changes.
- `/health` gains `server_id` and `server_name`.
- Verify: a zeroconf browser script sees the service with the right TXT records; connecting
  or renaming Plex re-announces; a loopback-only bind advertises nothing.

### M35 HTTPS (server, web) -- DONE 2026-09-14, not released yet

- Revised 2026-09-14 (no port 80 or 443): no Let's Encrypt in M35.
- Certificate store under `STATE_DIR/tls` (`app/tls.py`): one ECDSA P-256 key, made once and
  kept, and a self-signed certificate (2 years) whose names cover the public name, the
  hostname, `localhost` and the LAN addresses. The certificate is reissued with the same key
  at startup when those names change or it nears expiry, so the pin never changes. `TLS=auto`
  (default) turns HTTPS on for any bind that isn't loopback; plain HTTP only on loopback.
- Public address setting (`PUBLIC_HOST`, overridable in Settings) with the router-DDNS
  provider; `/health` and the mDNS TXT record gain `https` and the pin; Settings shows it.
- Secure cookies once HTTPS is on (no HSTS on a self-signed certificate).
- Verify: an HTTPS request with the pin matched succeeds and a wrong pin fails; the
  certificate names; a reissue after a name change keeps the pin; plain HTTP refused on a LAN
  bind.

### M36 Remote access via UPnP (server, web) -- code done 2026-09-15; router test waits for Liam; not released

- Revised 2026-09-15: libtorrent's port mapper can't be used from Python (its bindings raise a
  TypeError instead of returning mapping handles, and no port-map alerts arrived), so
  `app/upnp.py` is a small standard-library UPnP IGD client (SSDP discovery, the device
  description, AddPortMapping, GetSpecificPortMappingEntry, DeletePortMapping,
  GetExternalIPAddress). `app/remote_access.py` maps external `WEB_PORT` to `WEB_PORT` with a
  one-hour lease renewed every 10 minutes; status shows in Settings and `/api/remote-access`.
- Guard: refuses unless HTTPS is on with an unexpired certificate; turns itself off if it
  lapses. Only external port 40204 is ever mapped (never 80 or 443).
- NAT loopback check (Liam doesn't know whether the router does it): once mapped, the server
  requests `https://<public name>:40204/health` from inside and compares the `server_id`; the
  result shows in Settings and `/api/remote-access`, and the apps use it to decide whether the
  public address works at home.
- Verify: the mapping shows in the router's UPnP table; the server answers from mobile data;
  the mapping is removed when the server stops.

### M37 Device tokens (server, web) -- DONE 2026-09-14, not released yet

Status: done and verified on 2026-09-14 on LiamPC (server 0.8.1b, KDE client 0.5.0c, Android 0.7.0b with
versionCode 24; committed locally, not pushed or tagged). Signing in is enough to add a device; admins can
revoke (question 4, decided by Claude at Liam's request). `POST /api/auth/token` takes an optional
`{name, platform}` body, so apps from before M37 still sign in as "Unnamed device". New routes:
`GET /api/auth/devices`, `DELETE /api/auth/devices/{id}`, `DELETE /api/users/{id}/devices`; logout with a
token revokes it. `has_api_token` left the user JSON; the admin user list gains `device_count`.

- `device_tokens` table (user, device name, platform, token hash, created, last seen). An app
  sign-in creates one; the profile page lists and revokes them; the existing single
  `api_token` migrates to one device entry.
- Verify: two devices, revoke one, the other keeps working; tokens are hashed at rest.

### M38 Passkeys (server, web)

- `webauthn_credentials` table and a per-user WebAuthn user handle, generated for every user,
  Plex-linked ones included.
- Register passkeys on the profile page and sign in with them on the login page; a user who
  signed in with Plex can add a passkey and later sign in with it alone.
- `/.well-known/assetlinks.json` listing the Android app's release and debug signing
  certificates.
- Verify: register and sign in from a desktop browser and from the phone through the public
  name; a Plex user adds a passkey and signs in without Plex.

### M39 Android: find, remember, switch, passkeys

- Discovery on the connect screen (NsdManager with a multicast lock, only on Wi-Fi or
  Ethernet) listing servers by display name; manual URL entry stays.
- Remembered servers: id, name, LAN address, public address, pinned certificate and device
  token; automatic switching between the LAN and public addresses, re-checked when the
  network changes.
- HTTPS with pinning when connecting by LAN IP; a setup-required screen; passkey sign-in via
  Credential Manager.
- Verify: JVM tests for TXT parsing, address choice and pinning rules; an emulator walk (the
  emulator runs under KVM on the Strix Halo; its system image isn't installed yet); the real phone on Wi-Fi and on mobile data (needs
  Liam).

### M40 KDE: find, remember, switch, passkeys -- done 2026-09-15 except passkeys (after M48); desktop test waits for Liam

- `DiscoveredServersModel` over `zeroconf` (callbacks reach the Qt main thread through a
  signal), a server list on the login page, remembered servers in QSettings, LAN/public
  switching, pinning, a setup-required state, and passkey sign-in through the system browser.
- `python-zeroconf` joins the PKGBUILD depends.
- Verify: a headless check against a fake advertised service; QML harness; a real desktop
  pass on HoltOS (needs Liam).

### M14 Shakedown (Liam) -- after M40

The router, the DDNS name, the pinned certificate, UPnP and the NAT loopback check can only be
proven on the real network, so the shakedown folds in here. Passkeys are proven after M48.

### Then the Tier 3 queue

- **M41** Finish what shipped: per-title root folder and quality profile pickers (web, KDE,
  Android), usenet items on the Downloads page, a README note that music and books are out of
  scope.
- **M42** W2 torrent polish: per-torrent file selection, sequential download, IP filter,
  proxy, a session stats line.
- **M43** W8 Discover region and language.
- **M44** W9 anime: absolute episode numbering, Nyaa as the default for anime series, fansub
  group preference.
- **M45** W6 KDE: tray icon with download progress, a KRunner runner, Plasma notifications.
- **M46** W5 Android: home-screen widget and app shortcuts; Wear OS approve/decline last.
- **M47** W3 Jellyfin / Emby as an alternative to Plex, behind a media-server abstraction.

### M48 Cloudflare DNS (whenever the domain moves)

- Cloudflare provider: a scoped API token (Zone DNS edit) stored as a secret; the server
  updates the A/AAAA record when the external IP changes (port-map alerts plus a periodic
  check) and issues Let's Encrypt certificates by DNS-01, which needs no inbound port. This
  replaces the self-signed certificate and its key, so the apps accept the new trusted
  certificate once (re-pin, tied to the server id), and M38 passkeys follow.
- Passkeys are bound to the domain name: if the public name changes, every user registers
  their passkeys again. Flag this before switching.

## Versions

M33 is a breaking change (no anonymous mode), so the server goes to 0.8.0 and both apps
require it. Still no 1.0.0 until Liam asks.