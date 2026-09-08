# HoltOS Design System

The brand and interface system for HoltOS — an Arch-based, media-first distro that ships Plex, the *arr stack, ZFS and Plasma already wired up. Converted from the HoltOS brand system v1 document.

**Tone:** plain language over jargon, warmth in the type, precision in the data. Nunito 900 for display, JetBrains Mono for every path, label and number.

**Colour law:** purple (`--holt-current`) carries identity and does the shouting — one primary action per screen. Teal (`--holt-healthy`) only ever means online / healthy, never decoration. Amber (`--holt-warning`) means a human is needed.

## Foundations
- **Palette** — deep / surface / raised grounds, ink, current, healthy, warning
- **Typography** — Nunito 900/800/700/400 + JetBrains Mono
- **Principles** — the six rules the system is built on

## Components
- **Button** — primary / secondary / quiet / onCurrent, three sizes
- **StatusPill** — healthy, working, warning, idle
- **Panel** — surface container with mono eyebrow and meta slot
- **ServiceIcon** — one geometric primitive per service (plex, sonarr, radarr, prowlarr, qbit, zfs, podman, plasma)
- **OtterMark** — the mascot mark; expression lives in the eyes only, 38px floor
- **RingMark** — the reduced mark: the pool, an eye, a lens, a platter
- **Lockup** — wordmark plus mark, horizontal or stacked, optional teal tagline
- **PoolMeter** — storage ring with mono detail lines
- **ProgressRow** — queue and install progress
- **SelectRow** — setup-flow choice row with checkbox, path and status
- **MediaTile** — poster slot; placeholder art until real art lands

## Templates
- **Setup step** — the five-step first-boot flow shell
