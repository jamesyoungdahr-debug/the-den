"""GET/POST /api/settings as one `data` map (U4 rewrite: the field list is now the
backend's, not a hand-maintained copy that broke every time the API grew). Secrets are
never echoed back -- the backend sends has_* booleans -- and a blank secret on save
means "leave it alone", same rule as the web form."""

from __future__ import annotations

from PySide6.QtCore import Signal, Slot

from models.base import JsonRecord

SECRETS = ("tmdb_api_key", "discord_webhook_url")


class SettingsController(JsonRecord):
    saved = Signal()

    @Slot()
    def load(self) -> None:
        self._fetch("/api/settings")

    @Slot("QVariantMap")
    def save(self, values: dict) -> None:
        payload = {}
        for key, value in dict(values).items():
            if key in SECRETS:
                if value:
                    payload[key] = value
                continue
            payload[key] = value

        def on_done(status: int, body) -> None:
            if status == 200 and isinstance(body, dict):
                self._set_data(body)
                self.saved.emit()
            else:
                self.errorOccurred.emit(self.api.error_message(status, body))

        self.api.request("POST", "/api/settings", payload, on_done)

    @Slot()
    def scanPlex(self) -> None:
        def on_done(status: int, body) -> None:
            if status == 200:
                self.load()
            else:
                self.errorOccurred.emit(self.api.error_message(status, body))

        self.api.request("POST", "/api/plex/scan", on_done=on_done)
