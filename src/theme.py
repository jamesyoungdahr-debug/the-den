from PySide6.QtCore import Property, QObject

# The HoltOS design system's tokens (see the-den's design/styles.css), re-expressed as
# Qt properties instead of CSS custom properties -- same values, exposed to QML as the
# "Theme" context property so every .qml file can reference Theme.current, Theme.deep, etc.


class Theme(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    # Core surfaces
    deep = Property(str, lambda self: "#0D0B12", constant=True)
    surface = Property(str, lambda self: "#171423", constant=True)
    raised = Property(str, lambda self: "#1D1927", constant=True)
    # NOTE: Qt/QML parses 8-digit hex as #AARRGGBB (alpha first) -- the opposite of
    # CSS's #RRGGBBAA (alpha last). These are rgba(255,255,255, X) from styles.css,
    # recomputed into Qt's convention -- do not just copy hex out of the CSS file here.
    hairline = Property(str, lambda self: "#17FFFFFF", constant=True)  # rgba(255,255,255,.09)
    hairlineStrong = Property(str, lambda self: "#26FFFFFF", constant=True)  # rgba(255,255,255,.15)

    # Ink
    ink = Property(str, lambda self: "#FFFFFF", constant=True)
    ink70 = Property(str, lambda self: "#B3FFFFFF", constant=True)
    ink55 = Property(str, lambda self: "#8CFFFFFF", constant=True)
    ink42 = Property(str, lambda self: "#6BFFFFFF", constant=True)
    ink28 = Property(str, lambda self: "#47FFFFFF", constant=True)

    # Identity
    current = Property(str, lambda self: "#B14DFF", constant=True)
    currentDeep = Property(str, lambda self: "#8F2FE0", constant=True)
    lilac = Property(str, lambda self: "#F4EBFF", constant=True)

    # Semantic -- teal ONLY ever means online / healthy
    healthy = Property(str, lambda self: "#28E0C8", constant=True)
    warning = Property(str, lambda self: "#FFB84D", constant=True)

    # Type
    fontCore = Property(str, lambda self: "Nunito", constant=True)
    fontMono = Property(str, lambda self: "JetBrains Mono", constant=True)

    # Geometry
    radiusSm = Property(int, lambda self: 8, constant=True)
    radiusMd = Property(int, lambda self: 10, constant=True)
    radiusLg = Property(int, lambda self: 14, constant=True)
    radiusPill = Property(int, lambda self: 999, constant=True)

    # Rhythm
    space1 = Property(int, lambda self: 6, constant=True)
    space2 = Property(int, lambda self: 10, constant=True)
    space3 = Property(int, lambda self: 16, constant=True)
    space4 = Property(int, lambda self: 22, constant=True)
    space5 = Property(int, lambda self: 32, constant=True)
    space6 = Property(int, lambda self: 48, constant=True)
