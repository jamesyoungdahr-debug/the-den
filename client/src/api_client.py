"""The one connection to a running The Den backend: base URL, the signed-in account and
its API token, and the HTTP helper every model goes through.

Sign-in (U4): a local username/password goes to POST /api/auth/login, which starts a
cookie session; the client then asks POST /api/auth/token for a personal API token and
keeps only that (in QSettings), sending it as X-Api-Key from then on -- no password is
stored. "Sign in with Plex" uses the backend's PIN flow: POST /api/auth/plex/pin gives a
code and a plex.tv URL to open in the system browser; the client polls POST /api/auth/plex
until plex.tv reports the PIN claimed (202 while waiting). While the server runs with
sign-in optional, an anonymous connection is reported as an admin and everything works
without an account, exactly like the web UI."""

from __future__ import annotations

import json
from typing import Callable

from PySide6.QtCore import Property, QObject, QSettings, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

JSON = "application/json"
Callback = Callable[[int, object], None]  # (http status or -1, parsed body or error string)


class ApiClient(QObject):
    baseUrlChanged = Signal()
    connectedChanged = Signal()
    statusTextChanged = Signal()
    sessionChanged = Signal()
    busyChanged = Signal()
    plexPinChanged = Signal()
    loginFailed = Signal(str)

    def __init__(self, base_url: str | None = None, api_token: str | None = None, parent=None, persist: bool = True):
        super().__init__(parent)
        self._settings = QSettings("the-den", "client") if persist else None
        self._base_url = base_url or (self._settings.value("server/baseUrl", "http://127.0.0.1:8686") if self._settings else "http://127.0.0.1:8686")
        self._api_token = api_token if api_token is not None else (self._settings.value("server/apiToken", "") if self._settings else "")
        self._connected = False
        self._status_text = "Not connected"
        self._busy = False
        self._me: dict = {}
        self._server: dict = {}
        self._plex_pin: dict = {}
        self._plex_timer = QTimer(self)
        self._plex_timer.setInterval(2500)
        self._plex_timer.timeout.connect(self._poll_plex)
        self._manager = QNetworkAccessManager(self)
        self._request_seq = 0

    # ---- properties ----------------------------------------------------------------

    def _get_base_url(self) -> str:
        return self._base_url

    def _set_base_url(self, value: str) -> None:
        value = value.strip().rstrip("/")
        if value and value != self._base_url:
            self._base_url = value
            if self._settings:
                self._settings.setValue("server/baseUrl", value)
            self.baseUrlChanged.emit()

    baseUrl = Property(str, _get_base_url, _set_base_url, notify=baseUrlChanged)

    def _get_api_token(self) -> str:
        return self._api_token

    def _set_api_token(self, value: str) -> None:
        if value != self._api_token:
            self._api_token = value
            if self._settings:
                self._settings.setValue("server/apiToken", value)
            self.sessionChanged.emit()

    apiToken = Property(str, _get_api_token, _set_api_token, notify=sessionChanged)
    hasToken = Property(bool, lambda self: bool(self._api_token), notify=sessionChanged)

    connected = Property(bool, lambda self: self._connected, notify=connectedChanged)
    statusText = Property(str, lambda self: self._status_text, notify=statusTextChanged)
    busy = Property(bool, lambda self: self._busy, notify=busyChanged)

    # Who we are, per GET /api/auth/me
    signedIn = Property(bool, lambda self: bool(self._me) and not self._me.get("anonymous", False), notify=sessionChanged)
    canBrowse = Property(bool, lambda self: bool(self._me), notify=sessionChanged)  # signed in, or anonymous while sign-in is optional
    isAdmin = Property(bool, lambda self: bool(self._me.get("is_admin")), notify=sessionChanged)
    username = Property(str, lambda self: self._me.get("username") or "", notify=sessionChanged)
    userInitial = Property(str, lambda self: (self._me.get("username") or "?")[:1].upper(), notify=sessionChanged)
    authRequired = Property(bool, lambda self: bool(self._server.get("auth_required")), notify=sessionChanged)
    quota = Property("QVariantMap", lambda self: self._me.get("quota") or {}, notify=sessionChanged)
    me = Property("QVariantMap", lambda self: dict(self._me), notify=sessionChanged)

    # Plex PIN flow state for the login page
    plexCode = Property(str, lambda self: self._plex_pin.get("code", ""), notify=plexPinChanged)
    plexAuthUrl = Property(str, lambda self: self._plex_pin.get("auth_url", ""), notify=plexPinChanged)
    plexWaiting = Property(bool, lambda self: self._plex_timer.isActive(), notify=plexPinChanged)

    # ---- HTTP helper -----------------------------------------------------------------

    def request(self, method: str, path: str, payload: dict | None = None, on_done: Callback | None = None) -> QNetworkReply:
        """Fire an HTTP request and hand the parsed JSON (or an error string) to on_done.
        Every model uses this so the API token and base URL live in one place."""
        url = QUrl(f"{self._base_url}{path}")
        req = QNetworkRequest(url)
        req.setTransferTimeout(15000)
        if self._api_token:
            req.setRawHeader(b"X-Api-Key", self._api_token.encode())
        body = b""
        if payload is not None:
            req.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, JSON)
            body = json.dumps(payload).encode()
        method = method.upper()
        if method == "GET":
            reply = self._manager.get(req)
        elif method == "POST":
            reply = self._manager.post(req, body)
        elif method == "DELETE":
            reply = self._manager.deleteResource(req)
        elif method == "PATCH":
            reply = self._manager.sendCustomRequest(req, b"PATCH", body)
        else:
            raise ValueError(method)
        if on_done is not None:
            reply.finished.connect(lambda: self._finish(reply, on_done))
        else:
            reply.finished.connect(reply.deleteLater)
        return reply

    @staticmethod
    def _finish(reply: QNetworkReply, on_done: Callback) -> None:
        reply.deleteLater()
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        raw = bytes(reply.readAll().data())
        if status is None:
            on_done(-1, reply.errorString())
            return
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = raw.decode(errors="replace")
        on_done(int(status), parsed)

    @staticmethod
    def error_message(status: int, body) -> str:
        if status == -1:
            return str(body)
        if isinstance(body, dict) and body.get("detail"):
            detail = body["detail"]
            return detail if isinstance(detail, str) else json.dumps(detail)
        return f"HTTP {status}"

    def _set_busy(self, value: bool) -> None:
        if value != self._busy:
            self._busy = value
            self.busyChanged.emit()

    # ---- connect / session -------------------------------------------------------------

    @Slot()
    def checkHealth(self) -> None:
        """Reach the server, then find out who we are. Kept under its old name so the
        original M0 flow (and its tests) still work."""
        self._status_text = "Checking..."
        self.statusTextChanged.emit()
        self._request_seq += 1
        seq = self._request_seq
        self._set_busy(True)

        def on_health(status: int, body) -> None:
            if seq != self._request_seq:
                return  # superseded by a newer attempt
            if status == 200 and isinstance(body, dict) and body.get("status") == "ok":
                self._server = body
                self._connected = True
                self._status_text = "Connected"
                self.connectedChanged.emit()
                self.statusTextChanged.emit()
                self.refreshSession()
            else:
                self._server = {}
                self._connected = False
                self._me = {}
                self._status_text = "Connection failed: " + (self.error_message(status, body) if status != 200 else f"unexpected response: {body}")
                self._set_busy(False)
                self.connectedChanged.emit()
                self.statusTextChanged.emit()
                self.sessionChanged.emit()

        self.request("GET", "/health", on_done=on_health)

    @Slot()
    def refreshSession(self) -> None:
        def on_me(status: int, body) -> None:
            self._set_busy(False)
            if status == 200 and isinstance(body, dict):
                self._me = body
                self._server["auth_required"] = body.get("auth_required", self._server.get("auth_required"))
            else:
                self._me = {}
                if status == 401 and self._api_token:
                    # The stored token is no longer valid (regenerated on the web, user deleted).
                    self._api_token = ""
                    if self._settings:
                        self._settings.setValue("server/apiToken", "")
            self.sessionChanged.emit()

        self.request("GET", "/api/auth/me", on_done=on_me)

    @Slot(str, str)
    def login(self, username: str, password: str) -> None:
        """Local account: session cookie first, then swap it for a personal API token."""
        self._set_busy(True)

        def on_login(status: int, body) -> None:
            if status != 200:
                self._set_busy(False)
                self.loginFailed.emit(self.error_message(status, body) if status != 401 else "That username and password don't match.")
                return
            self._fetch_token()

        self.request("POST", "/api/auth/login", {"username": username, "password": password}, on_login)

    def _fetch_token(self) -> None:
        def on_token(status: int, body) -> None:
            if status == 200 and isinstance(body, dict) and body.get("api_token"):
                self._set_api_token(body["api_token"])
                self.refreshSession()
            else:
                self._set_busy(False)
                self.loginFailed.emit("Signed in, but couldn't get an API token: " + self.error_message(status, body))

        self.request("POST", "/api/auth/token", on_done=on_token)

    @Slot()
    def startPlexLogin(self) -> None:
        self._set_busy(True)

        def on_pin(status: int, body) -> None:
            if status != 200 or not isinstance(body, dict):
                self._set_busy(False)
                self.loginFailed.emit("Couldn't start Plex sign-in: " + self.error_message(status, body))
                return
            self._plex_pin = body
            self.plexPinChanged.emit()
            QDesktopServices.openUrl(QUrl(body["auth_url"]))
            self._plex_timer.start()
            self.plexPinChanged.emit()
            self._set_busy(False)

        self.request("POST", "/api/auth/plex/pin", on_done=on_pin)

    @Slot()
    def openPlexAuth(self) -> None:
        if self._plex_pin.get("auth_url"):
            QDesktopServices.openUrl(QUrl(self._plex_pin["auth_url"]))

    @Slot()
    def cancelPlexLogin(self) -> None:
        self._plex_timer.stop()
        self._plex_pin = {}
        self.plexPinChanged.emit()

    def _poll_plex(self) -> None:
        pin = self._plex_pin
        if not pin:
            self._plex_timer.stop()
            return

        def on_poll(status: int, body) -> None:
            if not self._plex_timer.isActive():
                return
            if status == 202:
                return  # not claimed yet; keep polling
            self._plex_timer.stop()
            self._plex_pin = {}
            self.plexPinChanged.emit()
            if status == 200:
                self._fetch_token()
            else:
                self.loginFailed.emit("Plex sign-in refused: " + self.error_message(status, body))

        self.request("POST", "/api/auth/plex", {"pin_id": pin["pin_id"], "code": pin["code"]}, on_poll)

    @Slot()
    def logout(self) -> None:
        self.cancelPlexLogin()
        self.request("POST", "/api/auth/logout")
        self._set_api_token("")
        self._me = {}
        self.sessionChanged.emit()
        self.refreshSession()  # anonymous may still be allowed in
