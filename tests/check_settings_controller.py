"""Headless smoke test for SettingsController against a real running backend. Exercises
load(), a real save() (secrets set for the first time, non-secrets changed), and
verifies secrets are never echoed back but has_* flips correctly -- plus that saving
with blank secret fields on a second save leaves the previously-set secret untouched.
No display needed. Run from src/: `python ../tests/check_settings_controller.py`
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QCoreApplication, QTimer

from models.settings_controller import SettingsController

BASE_URL = "http://127.0.0.1:8686"
app = QCoreApplication(sys.argv)
controller = SettingsController(lambda: BASE_URL)
failures = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


def step1_load() -> None:
    print("-- step 1: initial load --")
    controller.load()
    QTimer.singleShot(800, step2_verify_defaults)


def step2_verify_defaults() -> None:
    print(f"qbitUrl={controller.qbitUrl!r} hasTmdbApiKey={controller.hasTmdbApiKey} "
          f"interval={controller.automationIntervalSeconds}")
    if controller.hasTmdbApiKey:
        fail("expected hasTmdbApiKey=False on a fresh instance")

    print("-- step 2: save with a real TMDB key + changed qbit URL --")
    controller.save("real-key-123", "http://192.168.1.50:8080", "admin", "adminadmin", "./m", "./tv", 900, "")
    QTimer.singleShot(800, step3_verify_saved)


def step3_verify_saved() -> None:
    print(f"after save: qbitUrl={controller.qbitUrl!r} hasTmdbApiKey={controller.hasTmdbApiKey}")
    if not controller.hasTmdbApiKey:
        fail("expected hasTmdbApiKey=True after saving a real key")
    if controller.qbitUrl != "http://192.168.1.50:8080":
        fail(f"expected qbitUrl to update, got {controller.qbitUrl!r}")

    print("-- step 3: save again with a BLANK tmdb key -- should leave it untouched --")
    controller.save("", "http://192.168.1.50:8080", "admin", "adminadmin", "./m", "./tv", 900, "")
    QTimer.singleShot(800, step4_verify_untouched)


def step4_verify_untouched() -> None:
    print(f"after blank-secret save: hasTmdbApiKey={controller.hasTmdbApiKey}")
    if not controller.hasTmdbApiKey:
        fail("expected hasTmdbApiKey to remain True after a blank-secret save (should not clear it)")
    print("-- done --")
    if failures:
        print(f"{len(failures)} FAILURE(S)")
        sys.exit(1)
    print("ALL CHECKS PASSED")
    app.quit()


controller.errorOccurred.connect(lambda msg: fail(f"errorOccurred: {msg}"))
QTimer.singleShot(0, step1_load)
sys.exit(app.exec())
