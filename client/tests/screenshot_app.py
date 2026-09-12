"""Boots the real app (Main.qml + main.build_context) offscreen against a running
backend, walks through the shell (login -> discover -> each nav page -> a detail page),
and saves a PNG of each so the design can be checked without a desktop. Also fails on
any QML warning raised along the way.

    DEN_URL=... DEN_API_TOKEN=... python3 tests/screenshot_app.py [out_dir]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import Q_ARG, QMetaObject, QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402

from api_client import ApiClient  # noqa: E402
from main import build_context  # noqa: E402

BASE_URL = os.environ.get("DEN_URL", "http://127.0.0.1:8686")
TOKEN = os.environ.get("DEN_API_TOKEN", "")
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "screens")
QML = Path(__file__).resolve().parent.parent / "src" / "qml" / "Main.qml"

STEPS = [
    ("login", None),
    ("discover", "discover"),
    ("requests", "requests"),
    ("movies", "movies"),
    ("tv", "tv"),
    ("calendar", "calendar"),
    ("downloads", "downloads"),
    ("indexers", "indexers"),
    ("settings", "settings"),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    api = ApiClient(BASE_URL, TOKEN, persist=False)
    ctx = build_context(api)
    for name, obj in ctx.items():
        engine.rootContext().setContextProperty(name, obj)
    problems: list[str] = []
    engine.warnings.connect(lambda ws: problems.extend(w.toString() for w in ws))
    engine.load(QUrl.fromLocalFile(str(QML)))
    if not engine.rootObjects():
        print("FAIL: Main.qml did not load", problems)
        return 1
    window = engine.rootObjects()[0]
    queue = list(STEPS)

    def shoot(name: str) -> None:
        img = window.grabWindow()
        path = OUT / f"{name}.png"
        img.save(str(path))
        print(f"  saved {path} ({img.width()}x{img.height()})", flush=True)

    def step() -> None:
        if not queue:
            QMetaObject.invokeMethod(window, "openDetail", Q_ARG("QVariant", "tv"), Q_ARG("QVariant", 95396))
            QTimer.singleShot(3500, lambda: (shoot("detail"), finish()))
            return
        name, nav = queue.pop(0)
        if nav:
            QMetaObject.invokeMethod(window, "navigate", Q_ARG("QVariant", nav))
        QTimer.singleShot(3000, lambda: (shoot(name), step()))

    def finish() -> None:
        if problems:
            print(f"FAIL: {len(problems)} QML warning(s):")
            for p in problems:
                print("   ", p)
        else:
            print("PASS: no QML warnings across the whole walk")
        app.exit(1 if problems else 0)

    QTimer.singleShot(2500, step)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
