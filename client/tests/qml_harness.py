"""Headless QML harness: compiles every page (or one, given as argv[1]) against the real
model objects from main.build_context and a running backend, reports QML warnings,
and fails on any. Run with QT_QPA_PLATFORM=offscreen from client/:

    DEN_URL=http://127.0.0.1:8686 DEN_API_TOKEN=... python3 tests/qml_harness.py [Page.qml]

Each page is loaded inside a minimal window shell that provides applicationWindow(),
pageStack, navigate/push/openDetail/toast, so pages behave as they do under Main.qml.
Pages that take properties get sensible defaults (ids from the backend where needed)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

import json  # noqa: E402

from PySide6.QtCore import Q_ARG, Q_RETURN_ARG, QMetaObject, QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402

from api_client import ApiClient  # noqa: E402
from main import build_context  # noqa: E402

BASE_URL = os.environ.get("DEN_URL", "http://127.0.0.1:8686")
TOKEN = os.environ.get("DEN_API_TOKEN", "")
QML_DIR = Path(__file__).resolve().parent.parent / "src" / "qml"

PAGES = {
    "LoginPage.qml": {},
    "DiscoverPage.qml": {},
    "SearchPage.qml": {},
    "DetailPage.qml": {"kind": "tv", "tmdbId": 95396},
    "RequestsPage.qml": {},
    "MoviesPage.qml": {},
    "SeriesPage.qml": {},
    "EpisodesPage.qml": {"seriesId": 1, "seriesTitle": "Test series"},
    "CandidatesPage.qml": {"itemId": 1, "heading": "Test movie"},
    "CalendarPage.qml": {},
    "DownloadsPage.qml": {},
    "IndexersPage.qml": {},
    "SettingsPage.qml": {},
}

SHELL = """
import QtQuick
import QtQuick.Controls as Controls
Controls.ApplicationWindow {
    id: root
    width: 1200; height: 800; visible: true
    property alias pageStack: stack
    property var pageAction: null
    property string activeNav: ""
    property var lastToast: null
    property var lastNav: null
    function navigate(key) { lastNav = key }
    function push(page, props) { stack.push(Qt.resolvedUrl("%(qml)s/" + page), props || {}) }
    function openDetail(t, id) { lastNav = "detail:" + t + ":" + id }
    function search(q) { lastNav = "search:" + q }
    function toast(m, t) { lastToast = m }
    function loadPage(page, propsJson) { stack.replace(null, Qt.resolvedUrl("%(qml)s/" + page), JSON.parse(propsJson)) }
    function currentName() { return stack.currentItem ? stack.currentItem.objectName : "" }
    Controls.StackView { id: stack; anchors.fill: parent }
}
"""


def main() -> int:
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    api = ApiClient(BASE_URL, TOKEN, persist=False)
    ctx = build_context(api)
    for name, obj in ctx.items():
        engine.rootContext().setContextProperty(name, obj)

    problems: list[str] = []
    engine.warnings.connect(lambda ws: problems.extend(w.toString() for w in ws))

    shell_path = Path(__file__).resolve().parent / "_shell.qml"
    shell_path.write_text(SHELL % {"qml": QML_DIR.as_posix()})
    engine.load(QUrl.fromLocalFile(str(shell_path)))
    if not engine.rootObjects():
        print("FAIL: shell did not load", problems)
        return 1
    root = engine.rootObjects()[0]

    wanted = [sys.argv[1]] if len(sys.argv) > 1 else list(PAGES)
    results: dict[str, list[str]] = {}
    queue = list(wanted)

    def load_next() -> None:
        if not queue:
            finish()
            return
        page = queue.pop(0)
        problems.clear()
        props = PAGES.get(page, {})
        QMetaObject.invokeMethod(root, "loadPage", Q_ARG("QVariant", page), Q_ARG("QVariant", json.dumps(props)))

        def settle() -> None:
            name = QMetaObject.invokeMethod(root, "currentName", Q_RETURN_ARG("QVariant"))
            errs = list(problems)
            if not name:
                errs.append("no page item created (objectName empty)")
            results[page] = errs
            print(("  ok   " if not errs else "  FAIL ") + page + ("" if not errs else "\n         " + "\n         ".join(errs)))
            load_next()

        QTimer.singleShot(2500, settle)

    def finish() -> None:
        failed = [p for p, e in results.items() if e]
        print(f"\n{len(results) - len(failed)} pages clean, {len(failed)} with problems")
        app.exit(1 if failed else 0)

    api.checkHealth()
    QTimer.singleShot(1200, load_next)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
