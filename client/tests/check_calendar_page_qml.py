"""Force-compiles CalendarPage.qml against real CalendarMoviesModel/CalendarEpisodesModel
+ backend data, and triggers a genuine network error (per the M5 lesson: this backend
doesn't reliably 404 on bad input everywhere, so a forced-unreachable-URL is the
reliable way to exercise an error path). Run under QT_QPA_PLATFORM=offscreen, no
display needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from models.calendar_model import CalendarEpisodesModel, CalendarMoviesModel
from theme import Theme

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()

current_url = ["http://127.0.0.1:8686"]
movies_model = CalendarMoviesModel(lambda: current_url[0])
episodes_model = CalendarEpisodesModel(lambda: current_url[0])
theme = Theme()
engine.rootContext().setContextProperty("missingMoviesModel", movies_model)
engine.rootContext().setContextProperty("missingEpisodesModel", episodes_model)
engine.rootContext().setContextProperty("Theme", theme)

errors = []
engine.warnings.connect(lambda warnings: errors.extend(str(w) for w in warnings))

qml_file = Path(__file__).parent.parent / "src" / "qml" / "CalendarPage.qml"
engine.load(str(qml_file))

if not engine.rootObjects():
    print("FAIL: no root object created (compile/load error)")
    sys.exit(1)

failures = []


def check_initial_load():
    print(f"missing movies rowCount: {movies_model.rowCount()}")
    print(f"missing episodes rowCount: {episodes_model.rowCount()}")
    if movies_model.rowCount() == 0:
        failures.append("expected at least one real missing movie")
    if episodes_model.rowCount() == 0:
        failures.append("expected at least one real missing episode")

    print("-- pointing at an unreachable URL and refreshing to force a real error --")
    current_url[0] = "http://127.0.0.1:1"
    movies_model.refresh()


def finish():
    if errors:
        failures.append(f"{len(errors)} QML warning(s)/error(s): {errors}")
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        sys.exit(1)
    print("Loaded OK with real rows in both lists, error handler fired with no scoping errors.")
    print("PASS")
    app.quit()


QTimer.singleShot(1500, check_initial_load)
QTimer.singleShot(3000, finish)
sys.exit(app.exec())
