# The Den for Android — Privacy Policy

Last updated: 2026-09-12

The Den for Android ("the app", package `com.holtos.theden`) is a companion app for a
self-hosted The Den server that you run yourself. It is published by the HoltOS project.
This policy explains what the app stores and where it sends data.

## What the app stores on your device

- **Your server address** — the URL of your own The Den server.
- **A personal API token** — issued by your server when you sign in, so the app can
  make requests on your behalf without storing your password.

Both are kept in the app's private storage on your device. They are never sent anywhere
except to the server address you entered. Signing out deletes the token. Uninstalling
the app deletes everything.

The app does not store your Plex password or your local account password.

## Where the app sends data

- **Your The Den server.** Everything you do in the app (browsing, searching, requesting,
  and — for administrators — managing downloads, indexers and settings) is a request to
  the server you configured. What that server does with data is governed by whoever
  runs it; the server software is open source at
  https://github.com/jamesyoungdahr-debug/the-den.
- **plex.tv** (optional). If you choose *Sign in with Plex*, the app opens plex.tv in your
  system browser so you can approve the sign-in there. The app itself never sees your
  Plex credentials. Plex's own privacy policy applies to that page.
- **image.tmdb.org.** Poster and backdrop images for titles shown in Discover are loaded
  directly from The Movie Database's image servers. TMDB's privacy policy applies to
  those requests; the app sends nothing to TMDB beyond the standard image request.

## What the app does not do

- No analytics, crash reporting, advertising or tracking SDKs of any kind.
- No account with the publisher; there is no publisher-operated service behind the app.
- No access to contacts, location, camera, microphone, files or other device data. The
  only permissions requested are network access and network-state checks.
- No data is sold or shared with third parties.

## Children

The app is not directed at children and has no age-specific features.

## Changes

Changes to this policy are recorded in the repository history of this file.

## Contact

Questions: open an issue at https://github.com/jamesyoungdahr-debug/the-den/issues.
