"""Verifies Theme's color strings parse to the RGBA values the design system actually
specifies -- not just that they're valid hex. Qt's 8-digit hex is #AARRGGBB (alpha
first); CSS's rgba()/#RRGGBBAA puts alpha last. A value copied straight out of the CSS
file would be syntactically valid and silently wrong -- exactly what this catches.
No display needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtGui import QColor

from theme import Theme

theme = Theme()

# (property, expected r, g, b, expected alpha as a fraction 0-1, tolerance for rounding)
EXPECTATIONS = [
    ("deep", 0x0D, 0x0B, 0x12, 1.0),
    ("surface", 0x17, 0x14, 0x23, 1.0),
    ("raised", 0x1D, 0x19, 0x27, 1.0),
    ("hairline", 0xFF, 0xFF, 0xFF, 0.09),
    ("hairlineStrong", 0xFF, 0xFF, 0xFF, 0.15),
    ("ink", 0xFF, 0xFF, 0xFF, 1.0),
    ("ink70", 0xFF, 0xFF, 0xFF, 0.70),
    ("ink55", 0xFF, 0xFF, 0xFF, 0.55),
    ("ink42", 0xFF, 0xFF, 0xFF, 0.42),
    ("ink28", 0xFF, 0xFF, 0xFF, 0.28),
    ("current", 0xB1, 0x4D, 0xFF, 1.0),
    ("currentDeep", 0x8F, 0x2F, 0xE0, 1.0),
    ("lilac", 0xF4, 0xEB, 0xFF, 1.0),
    ("healthy", 0x28, 0xE0, 0xC8, 1.0),
    ("warning", 0xFF, 0xB8, 0x4D, 1.0),
]

failures = []
for prop_name, exp_r, exp_g, exp_b, exp_alpha_frac in EXPECTATIONS:
    hex_value = getattr(theme, prop_name)
    c = QColor(hex_value)
    if not c.isValid():
        failures.append(f"{prop_name}: '{hex_value}' is not a valid color")
        continue
    exp_alpha = round(exp_alpha_frac * 255)
    got = (c.red(), c.green(), c.blue(), c.alpha())
    want = (exp_r, exp_g, exp_b, exp_alpha)
    # allow +/-1 on alpha for rounding
    if got[:3] != want[:3] or abs(got[3] - want[3]) > 1:
        failures.append(f"{prop_name}: '{hex_value}' -> {got}, expected ~{want}")
    else:
        print(f"OK  {prop_name:16s} {hex_value} -> rgba{got}")

if failures:
    print(f"\n{len(failures)} FAILURE(S):")
    for f in failures:
        print(f"  FAIL: {f}")
    sys.exit(1)

print("\nALL COLOR CHECKS PASSED")
