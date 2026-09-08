"""Force-compiles IndexersPage.qml against a real IndexerListModel + backend.
Main.qml alone won't exercise this file since pageStack.push() is lazy -- run
under QT_QPA_PLATFORM=offscreen, no display needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from models.indexer_model import IndexerListModel

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
indexer_model = IndexerListModel(lambda: "http://127.0.0.1:8686")
engine.rootContext().setContextProperty("indexerModel", indexer_model)

errors = []
engine.warnings.connect(lambda warnings: errors.extend(str(w) for w in warnings))

qml_file = Path(__file__).parent.parent / "src" / "qml" / "IndexersPage.qml"
engine.load(str(qml_file))

if not engine.rootObjects():
    print("FAIL: no root object created (compile/load error)")
    sys.exit(1)

print(f"Loaded OK. QML warnings/errors: {errors or 'none'}")


def finish():
    if errors:
        print(f"FAIL: {len(errors)} QML warning(s)/error(s)")
        sys.exit(1)
    print("PASS")
    app.quit()


QTimer.singleShot(1500, finish)  # give the real refresh() call time to round-trip
sys.exit(app.exec())
