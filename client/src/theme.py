"""HoltOS Glass design tokens as Qt properties (the "Theme" context property in QML).

The values come straight from design/exports/holt_tokens.py, which design/build_tokens.py
generates from design/tokens.json -- the same source the web UI's holt-tokens.css and the
Android HoltTokens.kt come from, so the three never drift. When running from the repo the
file is found at ../../design/exports/; the Arch package copies it next to this module.

Colours are Qt-style '#AARRGGBB' strings (alpha FIRST); tests/check_theme_colors.py guards
that the exported values still parse to the RGBA the design system means."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from PySide6.QtCore import Property, QObject


def _load_tokens():
    here = Path(__file__).resolve().parent
    for candidate in (here / "holt_tokens.py", here.parents[1] / "design" / "exports" / "holt_tokens.py"):
        if candidate.exists():
            spec = importlib.util.spec_from_file_location("holt_tokens", candidate)
            module = importlib.util.module_from_spec(spec)
            sys.modules["holt_tokens"] = module
            spec.loader.exec_module(module)
            return module
    raise FileNotFoundError("holt_tokens.py not found next to theme.py or under design/exports/")


T = _load_tokens()


def _const(value):
    kind = bool if isinstance(value, bool) else int if isinstance(value, int) else float if isinstance(value, float) else str
    return Property(kind, lambda self, v=value: v, constant=True)


class Theme(QObject):
    """Every token QML needs, named like the web's --holt-* custom properties in camelCase."""

    # Core surfaces
    deep = _const(T.COLOR["deep"])
    surface = _const(T.COLOR["surface"])
    raised = _const(T.COLOR["raised"])
    hairline = _const(T.COLOR["hairline"])
    hairlineStrong = _const(T.COLOR["hairline_strong"])

    # Ink
    ink = _const(T.COLOR["ink"])
    ink70 = _const(T.COLOR["ink70"])
    ink55 = _const(T.COLOR["ink55"])
    ink42 = _const(T.COLOR["ink42"])
    ink28 = _const(T.COLOR["ink28"])

    # Identity
    current = _const(T.COLOR["current"])
    currentHover = _const(T.COLOR["current_hover"])
    currentDeep = _const(T.COLOR["current_deep"])
    currentTint = _const(T.COLOR["current_tint"])
    lilac = _const(T.COLOR["lilac"])

    # Semantic -- teal ONLY ever means online / healthy / available
    healthy = _const(T.COLOR["healthy"])
    warning = _const(T.COLOR["warning"])

    # Glass
    glassSurface = _const(T.GLASS["surface"])
    glassSurfaceStrong = _const(T.GLASS["surface_strong"])
    glassBorder = _const(T.GLASS["border"])
    glassBorderStrong = _const(T.GLASS["border_strong"])
    glassHighlight = _const(T.GLASS["highlight"])
    glassHighlightStrong = _const(T.GLASS["highlight_strong"])
    glassBadgeSurface = _const(T.GLASS["badge_surface"])
    glassInputSurface = _const(T.GLASS["input_surface"])
    glassBlur = _const(int(str(T.GLASS["blur"]).rstrip("px")))
    glassBlurStrong = _const(int(str(T.GLASS["blur_strong"]).rstrip("px")))

    # Ambient ground layer
    glowCurrent = _const(T.AMBIENT["glow_current"])
    glowHealthy = _const(T.AMBIENT["glow_healthy"])
    ring = _const(T.AMBIENT["ring"])
    scrimStrong = _const(T.AMBIENT["scrim_strong"])
    scrimMid = _const(T.AMBIENT["scrim_mid"])
    scrimWeak = _const(T.AMBIENT["scrim_weak"])

    # Badge tones
    badgeAvailable = _const(T.BADGE["available"])
    badgePending = _const(T.BADGE["pending"])
    badgeProcessing = _const(T.BADGE["processing"])
    badgePartial = _const(T.BADGE["partial"])
    badgeError = _const(T.BADGE["error"])
    badgeMissing = _const(T.BADGE["missing"])
    badgeMissingDot = _const(T.BADGE["missing_dot"])

    # Type
    fontCore = _const(T.FONT_CORE)
    fontMono = _const(T.FONT_MONO)
    sizeDisplay = _const(T.TYPE["display"]["size"])
    sizePageTitle = _const(T.TYPE["page_title"]["size"])
    sizeSectionTitle = _const(T.TYPE["section_title"]["size"])
    sizeWordmark = _const(T.TYPE["wordmark"]["size"])
    sizeBody = _const(T.TYPE["body"]["size"])
    sizeBodySmall = _const(T.TYPE["body_small"]["size"])
    sizeLabel = _const(int(round(T.TYPE["label"]["size"])))
    sizeButton = _const(int(round(T.TYPE["button"]["size"])))
    sizeEyebrow = _const(int(round(T.TYPE["eyebrow"]["size"])))
    sizeMeta = _const(int(round(T.TYPE["meta"]["size"])))
    trackingEyebrow = _const(float(T.TYPE["eyebrow"]["tracking"]))

    # Geometry
    radiusSm = _const(T.RADIUS["sm"])
    radiusMd = _const(T.RADIUS["md"])
    radiusLg = _const(T.RADIUS["lg"])
    radiusPill = _const(T.RADIUS["pill"])

    # Rhythm
    space1 = _const(T.SPACE["1"])
    space2 = _const(T.SPACE["2"])
    space3 = _const(T.SPACE["3"])
    space4 = _const(T.SPACE["4"])
    space5 = _const(T.SPACE["5"])
    space6 = _const(T.SPACE["6"])

    # Sizes
    sidebarWidth = _const(T.SIZE["sidebar"])
    sidebarRail = _const(T.SIZE["sidebarRail"])
    topBar = _const(T.SIZE["topBar"])
    posterSm = _const(T.SIZE["posterSm"])
    posterMd = _const(T.SIZE["posterMd"])
    posterLg = _const(T.SIZE["posterLg"])
    posterXl = _const(T.SIZE["posterXl"])
    avatar = _const(T.SIZE["avatar"])
    hitTarget = _const(T.SIZE["hitTarget"])
    mobileBreakpoint = _const(T.SIZE["mobileBreakpoint"])

    # Motion
    motionFast = _const(T.MOTION_MS["fast"])
    motionBase = _const(T.MOTION_MS["base"])
    motionDraw = _const(T.MOTION_MS["draw"])

    # Image bases (TMDB stores bare paths, TVmaze full URLs)
    tmdbPoster = _const("https://image.tmdb.org/t/p/w342")
    tmdbBackdrop = _const("https://image.tmdb.org/t/p/w1280")
    tmdbProfile = _const("https://image.tmdb.org/t/p/w185")
