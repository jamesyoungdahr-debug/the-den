from PySide6.QtCore import Signal, Slot

from models.base import JsonListModel


class IndexerListModel(JsonListModel):
    """Indexers -- GET/POST/DELETE /indexers and GET /indexers/{id}/test."""

    PATH = "/indexers"
    FIELDS = [
        ("indexerId", "id"),
        ("name", "name"),
        ("url", "url"),
        ("protocol", "protocol", "torznab"),
        ("indexerEnabled", "enabled", True),
    ]

    testResult = Signal(int, bool, str)  # indexer id, ok, message

    @Slot(str, str, str, str)
    def addIndexer(self, name: str, url: str, apiKey: str, protocol: str) -> None:
        payload = {"name": name.strip(), "url": url.strip(), "protocol": protocol or "torznab", "enabled": True}
        if apiKey:
            payload["api_key"] = apiKey
        self._write("POST", "/indexers", payload)

    @Slot(int)
    def deleteIndexer(self, indexerId: int) -> None:
        self._write("DELETE", f"/indexers/{indexerId}")

    @Slot(int)
    def testIndexer(self, indexerId: int) -> None:
        def on_done(status: int, body) -> None:
            if status == 200:
                ok = bool(body.get("ok", True)) if isinstance(body, dict) else True
                message = body.get("message") or body.get("detail") or "reachable" if isinstance(body, dict) else "reachable"
                self.testResult.emit(indexerId, ok, str(message))
            else:
                self.testResult.emit(indexerId, False, self.api.error_message(status, body))

        self.api.request("GET", f"/indexers/{indexerId}/test", on_done=on_done)
