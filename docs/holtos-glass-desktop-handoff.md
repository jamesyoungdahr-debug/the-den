# HoltOS glass for The Den client

Handoff from the HoltOS project, 2026-09-14. Liam wants The Den's KDE client
(the-den-client) to look like the HoltOS glass windows. This is the brief for
a the-den session. Nothing is built yet.

- Reference: `docs/design-references/glass-dolphin-reference.jpg` (Liam's
  target: Dolphin over a pink wallpaper).
- HoltOS source of truth: HoltOS repo, `docs/holtos-glass-design-plan.md`,
  section "Reference look".
- Values marked *provisional* are still being tuned in HoltOS's test VM.
  When HoltOS changes them, it updates this file.

## What the reference looks like

- One continuous pane of frosted glass. Title bar, toolbar, sidebar, tabs,
  content and status bar share one tint, and the blurred wallpaper shows
  through all of them evenly.
- No line between the title bar and the toolbar. Only faint hairlines, such
  as between the sidebar and the content.
- Selected and hovered items are translucent HoltOS purple with rounded
  corners (Liam, 2026-09-14; the screenshot uses white, HoltOS uses purple).
- White text; section labels dimmer.
- Rounded window corners (10 px) with a faint light 1 px outline.
- Title bar buttons are HoltOS's red, yellow and green circles on the right
  with a hover glow. KWin's window decoration draws them, so the client does
  nothing for them.

## How HoltOS makes the glass

- KWin (holtos-kwin) blurs behind every window: `ForceBlur=true` in
  `/etc/xdg/kwinrc`, BlurStrength 15, noise being reduced.
- The glass only shows where an app paints translucently. Any opaque fill
  hides the blur behind it.
- QtWidgets apps get their tint from the Kvantum theme HoltOSGlass: the
  window fill is holt-surface `#171423` at 40 % (*provisional*, being made
  lighter to match the reference), and views add no second layer.
- Kirigami and Qt Quick apps are not covered by the theme yet (HoltOS
  milestone G7), so the client has to do this itself.

## The client today

- `src/qml/Main.qml`: `Controls.ApplicationWindow` with `color: Theme.deep`
  and `background: Ground {}`, so the window is opaque.
- `src/qml/holt/Ground.qml`: an opaque `Theme.deep` fill with two ambient
  glows and a ring. This is the drawn "fake glass" ground.
- `src/qml/holt/GlassPanel.qml`, the sidebar (Main.qml, about line 129) and
  the top bar (about line 237) paint `glassSurface` (70 %) or
  `glassSurfaceStrong` (84 %) over that ground.

So the desktop is never blurred through the client, and its glass is darker
than HoltOS's.

## Proposed changes

1. **A real translucent window on HoltOS.** Decide `glassMode` once at
   startup: true when `/etc/os-release` has `ID=holtos` and a compositor is
   running (a Wayland session, or X11 with a compositing manager). In glass
   mode, call `QQuickWindow.setDefaultAlphaBuffer(True)` in `src/main.py`
   before the `QGuiApplication` is created, and set the ApplicationWindow's
   `color` to `"transparent"`. KWin's force-blur then blurs the desktop
   behind the window. Expose `glassMode` to QML (for example on `Theme`).
2. **Ground only outside HoltOS.** In glass mode the window background is one
   tint rectangle (`desktopGlass.window`), not `Ground`. Everywhere else
   (other desktops, no compositor) keep `Ground` exactly as it is.
3. **One layer.** In glass mode the sidebar, top bar and page background
   paint nothing of their own. They are separated by hairlines only, like
   Dolphin's sidebar and toolbar. Cards and dialogs (`GlassPanel`) keep a
   light raised layer, `desktopGlass.raised`.
4. **Selection and hover in translucent purple.** Selected:
   `desktopGlass.selection`; hovered: `desktopGlass.hover`; both with
   `radius.sm` corners. Keep the 2 px purple accent bar on the active
   navigation item.
5. **Tokens: a new `desktopGlass` group in `design/tokens.json`.** Do not
   change `glass`: it also drives the web UI and the Android app, which draw
   their own ground. `design/build_tokens.py` must emit the group into the
   client's `holt_tokens.py` as Qt `#AARRGGBB` (alpha first;
   `tests/check_theme_colors.py` guards this). The web and Android exports
   can ignore it.

   | Token | Value | Use |
   |---|---|---|
   | `window` | `rgba(23,20,35,.40)` *provisional* | the single window tint; must match HoltOS's Kvantum window fill |
   | `raised` | `rgba(29,25,39,.30)` *provisional* | cards and dialogs |
   | `selection` | `rgba(177,77,255,.22)` | selected items |
   | `hover` | `rgba(177,77,255,.12)` | hovered items |
   | `border` | `rgba(255,255,255,.09)` | hairlines (same as `color.hairline`) |
   | `windowOpaque` | `#171423` | no compositor, or reduced transparency |

6. **Readability.** Glass over a bright wallpaper can push white text below
   4.5:1 contrast. HoltOS is adding a brightness clamp to KWin's blur
   (milestones G8 and G9), which will help every app without client
   changes. Until then, use `ink` for primary labels on glass rather than
   `ink55`, and add a subtle text shadow to small labels if the VM check
   shows a problem.
7. **Images stay opaque.** Posters and the Detail backdrop hero are content,
   not chrome; only panels and the shell become glass.

## Verify

- `tests/run_all.sh` and `tests/qml_harness.py` stay clean (no QML warnings).
- `tests/screenshot_app.py` runs offscreen and cannot show a blur. Add a
  glass-mode run that draws a bright test image under the window, to check
  text contrast.
- On screen: the HoltOS test VM (software rendering, so it shows the look
  but not performance) or Liamtab. Put The Den next to Dolphin over a bright
  wallpaper. The tints must match, with no visible band between the sidebar,
  top bar and content.
- Release it as a client version through the HoltOS updater, following
  the-den's release rules.

## Still open

- The final window tint and blur strength. HoltOS tunes them in its VM and
  updates the *provisional* values above.
