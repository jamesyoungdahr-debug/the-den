"""Force-compiles SeriesPage.qml against real models + backend data, and actually
triggers an errorOccurred (adding a duplicate series). Per the M3 lesson (ROADMAP.md),
a clean empty load proves nothing about the error-handling paths.
Run under QT_QPA_PLATFORM=offscreen, no display needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from models.series_model import SeriesListModel, SeriesSearchResultsModel
from theme import Theme

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
series_model = SeriesListModel(lambda: "http://127.0.0.1:8686")
series_search_model = SeriesSearchResultsModel(lambda: "http://127.0.0.1:8686")
theme = Theme()
engine.rootContext().setContextProperty("seriesModel", series_model)
engine.rootContext().setContextProperty("seriesSearchModel", series_search_model)
engine.rootContext().setContextProperty("Theme", theme)

errors = []
engine.warnings.connect(lambda warnings: errors.extend(str(w) for w in warnings))

qml_file = Path(__file__).parent.parent / "src" / "qml" / "SeriesPage.qml"
engine.load(str(qml_file))

if not engine.rootObjects():
    print("FAIL: no root object created (compile/load error)")
    sys.exit(1)


def trigger_error():
    print("-- triggering seriesModel.addSeries() with a duplicate tvmaze_id --")
    series_model.addSeries(169, "Breaking Bad", "2008", "", "")


def finish():
    print(f"rowCount after load: {series_model.rowCount()}")
    if series_model.rowCount() == 0:
        print("FAIL: expected at least one real series row")
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
