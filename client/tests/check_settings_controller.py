"""Headless smoke test for SettingsController (U4 shape: one `data` map) against a real
running backend. Exercises load(), a real save() with a changed non-secret and a
first-time secret, verifies the secret is never echoed back but has_* flips, then
saves again with the secret blank and checks it was left alone. Restores the changed
value at the end. No display needed.

    DEN_URL=http://127.0.0.1:8686 DEN_API_TOKEN=... python3 tests/check_settings_controller.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QCoreApplication, QTimer

from api_client import ApiClient
from models.settings_controller import SettingsController

BASE_URL = os.environ.get("DEN_URL", "http://127.0.0.1:8686")
TOKEN = os.environ.get("DEN_API_TOKEN", "")
app = QCoreApplication(sys.argv)
api = ApiClient(BASE_URL, TOKEN, persist=False)
controller = SettingsController(api)
controller.errorOccurred.connect(lambda m: fail(f"errorOccurred: {m}"))
failures = []
original_interval = None


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


def step1_load() -> None:
    print("-- step 1: load --")
    controller.load()
    QTimer.singleShot(1000, step2_save)


def step2_save() -> None:
    global original_interval
    d = controller.data
    print(f"loaded keys: {len(d)}; has_discord_webhook={d.get('has_discord_webhook')} interval={d.get('automation_interval_seconds')}")
    if "automation_interval_seconds" not in d or "has_tmdb_api_key" not in d:
        fail("expected the settings record to include automation_interval_seconds and has_tmdb_api_key")
    original_interval = d.get("automation_interval_seconds")
    print("-- step 2: save a changed interval + a first-time Discord webhook --")
    controller.save({"automation_interval_seconds": 1234, "discord_webhook_url": "https://discord.invalid/hook/test"})
    QTimer.singleShot(1000, step3_verify)


def step3_verify() -> None:
    d = controller.data
    print(f"after save: interval={d.get('automation_interval_seconds')} has_discord_webhook={d.get('has_discord_webhook')} webhook_echo={d.get('discord_webhook_url')!r}")
    if d.get("automation_interval_seconds") != 1234:
        fail("interval did not update")
    if not d.get("has_discord_webhook"):
        fail("has_discord_webhook should be True after saving one")
    if d.get("discord_webhook_url"):
        fail("secret must never be echoed back")
    print("-- step 3: save again with the secret blank; it must be left alone --")
    controller.save({"automation_interval_seconds": original_interval or 900, "discord_webhook_url": ""})
    QTimer.singleShot(1000, step4_done)


def step4_done() -> None:
    d = controller.data
    if not d.get("has_discord_webhook"):
        fail("blank secret on save must not clear the stored webhook")
    if d.get("automation_interval_seconds") != (original_interval or 900):
        fail("interval was not restored")
    print("PASS" if not failures else f"{len(failures)} failure(s)")
    app.exit(1 if failures else 0)


QTimer.singleShot(0, step1_load)
sys.exit(app.exec())
