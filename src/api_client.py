from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


class ApiClient(QObject):
    """Talks to a running The Den backend over its existing JSON API.
    Network calls go through QNetworkAccessManager (Qt's own async HTTP client)
    so they never block the UI thread — no extra Python HTTP library needed."""

    connectedChanged = Signal()
    statusTextChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._base_url = "http://127.0.0.1:8686"
        self._connected = False
        self._status_text = "Not connected"
        self._manager = QNetworkAccessManager(self)

    def _get_base_url(self) -> str:
        return self._base_url

    def _set_base_url(self, value: str) -> None:
        self._base_url = value

    baseUrl = Property(str, _get_base_url, _set_base_url)

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
        request = QNetworkRequest(QUrl(f"{self._base_url}/health"))
        reply = self._manager.get(request)
        reply.finished.connect(lambda: self._on_health_reply(reply))

    def _on_health_reply(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            body = bytes(reply.readAll().data()).decode()
            self._connected = '"status":"ok"' in body
            self._status_text = "Connected" if self._connected else f"Unexpected response: {body}"
        else:
            self._connected = False
            self._status_text = f"Connection failed: {reply.errorString()}"
        reply.deleteLater()
        self.connectedChanged.emit()
        self.statusTextChanged.emit()
