import json

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

_JSON_CONTENT_TYPE = "application/json"


class SettingsController(QObject):
    """Backed by GET/POST /api/settings. Not a list model -- a single record, so a
    plain QObject with Qt Properties (NOTIFY-backed so QML text fields update once
    load() returns) rather than a QAbstractListModel. Secret fields (TMDB key, qBit
    password, Discord webhook) are never echoed back by the backend -- only a
    has_* boolean -- matching the same rule the web UI's settings form follows."""

    qbitUrlChanged = Signal()
    qbitUsernameChanged = Signal()
    moviesRootChanged = Signal()
    tvRootChanged = Signal()
    automationIntervalSecondsChanged = Signal()
    hasTmdbApiKeyChanged = Signal()
    hasQbitPasswordChanged = Signal()
    hasDiscordWebhookChanged = Signal()

    errorOccurred = Signal(str)
    saved = Signal()

    def __init__(self, base_url_provider, parent=None):
        super().__init__(parent)
        self._manager = QNetworkAccessManager(self)
        self._base_url = base_url_provider
        self._qbit_url = ""
        self._qbit_username = ""
        self._movies_root = ""
        self._tv_root = ""
        self._automation_interval_seconds = 900
        self._has_tmdb_api_key = False
        self._has_qbit_password = False
        self._has_discord_webhook = False

    def _get_qbit_url(self) -> str:
        return self._qbit_url

    qbitUrl = Property(str, _get_qbit_url, notify=qbitUrlChanged)

    def _get_qbit_username(self) -> str:
        return self._qbit_username

    qbitUsername = Property(str, _get_qbit_username, notify=qbitUsernameChanged)

    def _get_movies_root(self) -> str:
        return self._movies_root

    moviesRoot = Property(str, _get_movies_root, notify=moviesRootChanged)

    def _get_tv_root(self) -> str:
        return self._tv_root

    tvRoot = Property(str, _get_tv_root, notify=tvRootChanged)

    def _get_automation_interval_seconds(self) -> int:
        return self._automation_interval_seconds

    automationIntervalSeconds = Property(int, _get_automation_interval_seconds, notify=automationIntervalSecondsChanged)

    def _get_has_tmdb_api_key(self) -> bool:
        return self._has_tmdb_api_key

    hasTmdbApiKey = Property(bool, _get_has_tmdb_api_key, notify=hasTmdbApiKeyChanged)

    def _get_has_qbit_password(self) -> bool:
        return self._has_qbit_password

    hasQbitPassword = Property(bool, _get_has_qbit_password, notify=hasQbitPasswordChanged)

    def _get_has_discord_webhook(self) -> bool:
        return self._has_discord_webhook

    hasDiscordWebhook = Property(bool, _get_has_discord_webhook, notify=hasDiscordWebhookChanged)

    @Slot()
    def load(self) -> None:
        reply = self._manager.get(QNetworkRequest(QUrl(f"{self._base_url()}/api/settings")))
        reply.finished.connect(lambda: self._on_reply(reply, emit_saved=False))

    @Slot(str, str, str, str, str, str, int, str)
    def save(
        self,
        tmdbApiKey: str,
        qbitUrl: str,
        qbitUsername: str,
        qbitPassword: str,
        moviesRoot: str,
        tvRoot: str,
        automationIntervalSeconds: int,
        discordWebhookUrl: str,
    ) -> None:
        payload = {
            "qbit_url": qbitUrl,
            "qbit_username": qbitUsername,
            "movies_root": moviesRoot,
            "tv_root": tvRoot,
            "automation_interval_seconds": automationIntervalSeconds,
        }
        # Secret fields: only send if the user actually typed something new -- an
        # empty string here means "leave the stored value alone", same rule the
        # backend and the web UI both already follow.
        if tmdbApiKey:
            payload["tmdb_api_key"] = tmdbApiKey
        if qbitPassword:
            payload["qbit_password"] = qbitPassword
        if discordWebhookUrl:
            payload["discord_webhook_url"] = discordWebhookUrl

        request = QNetworkRequest(QUrl(f"{self._base_url()}/api/settings"))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, _JSON_CONTENT_TYPE)
        reply = self._manager.post(request, json.dumps(payload).encode())
        reply.finished.connect(lambda: self._on_reply(reply, emit_saved=True))

    def _on_reply(self, reply: QNetworkReply, emit_saved: bool) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            body = bytes(reply.readAll().data())
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {}
            self._apply(data)
            if emit_saved:
                self.saved.emit()
        else:
            self.errorOccurred.emit(reply.errorString())
        reply.deleteLater()

    def _apply(self, data: dict) -> None:
        if data.get("qbit_url", self._qbit_url) != self._qbit_url:
            self._qbit_url = data.get("qbit_url", "")
            self.qbitUrlChanged.emit()
        if data.get("qbit_username", self._qbit_username) != self._qbit_username:
            self._qbit_username = data.get("qbit_username", "")
            self.qbitUsernameChanged.emit()
        if data.get("movies_root", self._movies_root) != self._movies_root:
            self._movies_root = data.get("movies_root", "")
            self.moviesRootChanged.emit()
        if data.get("tv_root", self._tv_root) != self._tv_root:
            self._tv_root = data.get("tv_root", "")
            self.tvRootChanged.emit()
        new_interval = data.get("automation_interval_seconds", self._automation_interval_seconds)
        if new_interval != self._automation_interval_seconds:
            self._automation_interval_seconds = new_interval
            self.automationIntervalSecondsChanged.emit()
        if data.get("has_tmdb_api_key", self._has_tmdb_api_key) != self._has_tmdb_api_key:
            self._has_tmdb_api_key = data.get("has_tmdb_api_key", False)
            self.hasTmdbApiKeyChanged.emit()
        if data.get("has_qbit_password", self._has_qbit_password) != self._has_qbit_password:
            self._has_qbit_password = data.get("has_qbit_password", False)
            self.hasQbitPasswordChanged.emit()
        if data.get("has_discord_webhook", self._has_discord_webhook) != self._has_discord_webhook:
            self._has_discord_webhook = data.get("has_discord_webhook", False)
            self.hasDiscordWebhookChanged.emit()
