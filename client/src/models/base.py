"""The list-model base every screen shares (U4). Subclasses declare FIELDS -- the QML
role name, the JSON key it reads and a default -- and a PATH; the base handles roles,
fetching through the ApiClient (so the API token is always sent), the out-of-order-reply
guard that CandidatesModel and ApiClient grew in the review-fix pass (now everywhere,
for free), a `loading` flag for skeletons, `count` for empty states, and `get(row)` for
delegates that want the whole record."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Property, QAbstractListModel, QModelIndex, QObject, Qt, Signal, Slot

from api_client import ApiClient

Field = tuple  # (roleName, jsonKey, default)


class JsonListModel(QAbstractListModel):
    FIELDS: list[Field] = []
    PATH: str = ""

    errorOccurred = Signal(str)
    countChanged = Signal()
    loadingChanged = Signal()
    loaded = Signal()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # MovieListModel.TitleRole-style constants for tests and Python callers.
        for i, field in enumerate(cls.FIELDS):
            name = field[0]
            setattr(cls, name[0].upper() + name[1:] + "Role", Qt.ItemDataRole.UserRole + 1 + i)

    def __init__(self, api: ApiClient, parent: QObject | None = None):
        super().__init__(parent)
        self.api = api
        self._items: list[dict] = []
        self._loading = False
        self._seq = 0
        self._roles = {Qt.ItemDataRole.UserRole + 1 + i: f for i, f in enumerate(self.FIELDS)}

    # ---- Qt model plumbing ---------------------------------------------------------------

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int):
        if not index.isValid():
            return None
        field = self._roles.get(role)
        if field is None:
            return None
        item = self._items[index.row()]
        name, key = field[0], field[1]
        default = field[2] if len(field) > 2 else None
        value = item.get(key, default)
        return default if value is None else value

    def roleNames(self):
        return {role: f[0].encode() for role, f in self._roles.items()}

    count = Property(int, lambda self: len(self._items), notify=countChanged)
    loading = Property(bool, lambda self: self._loading, notify=loadingChanged)

    @Slot(int, result="QVariant")
    def get(self, row: int):
        return dict(self._items[row]) if 0 <= row < len(self._items) else {}

    def items(self) -> list[dict]:
        return list(self._items)

    # ---- fetching ------------------------------------------------------------------------

    def _set_loading(self, value: bool) -> None:
        if value != self._loading:
            self._loading = value
            self.loadingChanged.emit()

    def _set_items(self, items: list[dict]) -> None:
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()
        self.countChanged.emit()
        self.loaded.emit()

    def _fetch(self, path: str, transform: Callable[[Any], list[dict]] | None = None) -> None:
        self._seq += 1
        seq = self._seq
        self._set_loading(True)

        def on_done(status: int, body) -> None:
            if seq != self._seq:
                return  # a newer fetch superseded this reply; whatever is on screen isn't for it
            self._set_loading(False)
            if status == 200:
                items = body if isinstance(body, list) else []
                if transform is not None:
                    items = transform(body)
                self._set_items(items)
            else:
                self.errorOccurred.emit(self.api.error_message(status, body))

        self.api.request("GET", path, on_done=on_done)

    def _write(self, method: str, path: str, payload: dict | None = None, refresh: bool = True,
               on_done: Callable[[int, Any], None] | None = None) -> None:
        def done(status: int, body) -> None:
            if status not in (200, 201, 204):
                self.errorOccurred.emit(self.api.error_message(status, body))
            if on_done is not None:
                on_done(status, body)
            if refresh:
                self.refresh()

        self.api.request(method, path, payload, done)

    @Slot()
    def refresh(self) -> None:
        if self.PATH:
            self._fetch(self.PATH)


class JsonRecord(QObject):
    """A single JSON record exposed to QML as one `data` map (plus loading/error), for
    detail pages and settings where a list model is the wrong shape."""

    dataChanged = Signal()
    loadingChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(self, api: ApiClient, parent: QObject | None = None):
        super().__init__(parent)
        self.api = api
        self._data: dict = {}
        self._loading = False
        self._seq = 0

    data = Property("QVariantMap", lambda self: dict(self._data), notify=dataChanged)
    loading = Property(bool, lambda self: self._loading, notify=loadingChanged)
    hasData = Property(bool, lambda self: bool(self._data), notify=dataChanged)

    def _set_loading(self, value: bool) -> None:
        if value != self._loading:
            self._loading = value
            self.loadingChanged.emit()

    def _set_data(self, data: dict) -> None:
        self._data = dict(data) if isinstance(data, dict) else {}
        self.dataChanged.emit()

    def _fetch(self, path: str) -> None:
        self._seq += 1
        seq = self._seq
        self._set_loading(True)

        def on_done(status: int, body) -> None:
            if seq != self._seq:
                return
            self._set_loading(False)
            if status == 200 and isinstance(body, dict):
                self._set_data(body)
            else:
                self.errorOccurred.emit(self.api.error_message(status, body))

        self.api.request("GET", path, on_done=on_done)
