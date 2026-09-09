from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


class ApiClient(QObject):
    """Talks to a running The Den backend over its existing JSON API.
    Network calls go through QNetworkAccessManager (Qt's own async HTTP client)
    so they never block the UI thread — no extra Python HTTP library needed."""

    baseUrlChanged = Signal()
    connectedChanged = Signal()
    statusTextChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._base_url = "http://127.0.0.1:8686"
        self._connected = False
        self._status_text = "Not connected"
        self._manager = QNetworkAccessManager(self)
        # Bumped on every checkHealth() so a reply from a superseded check (e.g. the
        # user fixed a typo'd URL and clicked Connect again while the first, now-stale
        # attempt was still timing out) can be dropped instead of overwriting a newer,
        # correct result with a stale one.
        self._request_seq = 0

    def _get_base_url(self) -> str:
        return self._base_url

    def _set_base_url(self, value: str) -> None:
        if value != self._base_url:
            self._base_url = value
            self.baseUrlChanged.emit()

    baseUrl = Property(str, _get_base_url, _set_base_url, notify=baseUrlChanged)

    def _get_connected(self) -> bool:
        return self._connected

    connected = Property(bool, _get_connected, notify=connectedChanged)

    def _get_status_text(self) -> str:
        return self._status_text

    statusText = Property(str, _get_status_text, notify=statusTextChanged)

    @Slot()
    def checkHealth(self) -> None:
        self._status_text = "Checking..."
        self.statusTextChanged.emit()
        self._request_seq += 1
        seq = self._request_seq
        request = QNetworkRequest(QUrl(f"{self._base_url}/health"))
        reply = self._manager.get(request)
        reply.finished.connect(lambda: self._on_health_reply(reply, seq))

    def _on_health_reply(self, reply: QNetworkReply, seq: int) -> None:
        reply.deleteLater()
        if seq != self._request_seq:
            # A newer checkHealth() has already superseded this one -- e.g. the user
            # corrected the URL and clicked Connect again while this one was still
            # working through a timeout. Drop it rather than clobbering the newer
            # (possibly successful) result with this stale one.
            return
        if reply.error() == QNetworkReply.NetworkError.NoError:
            body = bytes(reply.readAll().data()).decode()
            self._connected = '"status":"ok"' in body
            self._status_text = "Connected" if self._connected else f"Unexpected response: {body}"
        else:
            self._connected = False
            self._status_text = f"Connection failed: {reply.errorString()}"
        self.connectedChanged.emit()
        self.statusTextChanged.emit()
