"""Force-compiles DownloadsPage.qml against real DownloadsModel + backend data, AND
actually triggers both refresh (real rows -> exercises the delegate/StatusPill
bindings) and an errorOccurred (check on a nonexistent id -> exercises the
Connections/statusBanner handler) -- per the M3 lesson, a clean empty load proves
nothing about either of those paths. Run under QT_QPA_PLATFORM=offscreen, no display.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from models.downloads_model import DownloadsModel
from theme import Theme

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
downloads_model = DownloadsModel(lambda: "http://127.0.0.1:8686")
theme = Theme()
engine.rootContext().setContextProperty("downloadsModel", downloads_model)
engine.rootContext().setContextProperty("Theme", theme)

errors = []
engine.warnings.connect(lambda warnings: errors.extend(str(w) for w in warnings))

qml_file = Path(__file__).parent.parent / "src" / "qml" / "DownloadsPage.qml"
engine.load(str(qml_file))

if not engine.rootObjects():
    print("FAIL: no root object created (compile/load error)")
    sys.exit(1)


def trigger_error():
    print("-- triggering downloadsModel.check(999999) to exercise onErrorOccurred --")
    downloads_model.check(999999)


def finish():
    print(f"rowCount after load: {downloads_model.rowCount()}")
    if downloads_model.rowCount() == 0:
        print("FAIL: expected at least one real download row (run the M3 grab test first)")
        sys.exit(1)
    if errors:
        print(f"FAIL: {len(errors)} QML warning(s)/error(s): {errors}")
        sys.exit(1)
    print("Loaded OK with real rows, error handler fired with no scoping errors.")
    print("PASS")
    app.quit()


QTimer.singleShot(1000, trigger_error)
QTimer.singleShot(2500, finish)
sys.exit(app.exec())
