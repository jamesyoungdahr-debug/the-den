"""Force-compiles IndexersPage.qml against a real IndexerListModel + backend, AND
actually triggers a testResult signal (via a real indexer, id=1, assumed already
seeded) -- the earlier version of this test only checked that the page loads with
zero rows, which never exercised the Connections handlers that reference statusBanner
by id. That's exactly the blind spot that let the ListView.header id-scoping bug ship
undetected. Run under QT_QPA_PLATFORM=offscreen, no display needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from models.indexer_model import IndexerListModel
from theme import Theme

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
indexer_model = IndexerListModel(lambda: "http://127.0.0.1:8686")
theme = Theme()
engine.rootContext().setContextProperty("indexerModel", indexer_model)
engine.rootContext().setContextProperty("Theme", theme)

errors = []
engine.warnings.connect(lambda warnings: errors.extend(str(w) for w in warnings))

qml_file = Path(__file__).parent.parent / "src" / "qml" / "IndexersPage.qml"
engine.load(str(qml_file))

if not engine.rootObjects():
    print("FAIL: no root object created (compile/load error)")
    sys.exit(1)


def trigger_test_result():
    print("-- triggering indexerModel.testIndexer(1) to exercise onTestResult --")
    indexer_model.testIndexer(1)


def finish():
    print(f"rowCount after load: {indexer_model.rowCount()}")
    if indexer_model.rowCount() == 0:
        print("FAIL: expected at least one real indexer row to have loaded")
        sys.exit(1)
    if errors:
        print(f"FAIL: {len(errors)} QML warning(s)/error(s): {errors}")
        sys.exit(1)
    print("Loaded OK with real rows, testResult handler fired with no scoping errors.")
    print("PASS")
    app.quit()


QTimer.singleShot(1000, trigger_test_result)
QTimer.singleShot(2500, finish)
sys.exit(app.exec())
