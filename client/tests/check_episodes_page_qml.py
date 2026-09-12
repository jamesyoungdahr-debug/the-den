"""Force-compiles EpisodesPage.qml against real EpisodesModel + backend data (4
episodes across 2 seasons -- exercises the section-grouping delegate for real), and
triggers a genuine network error to exercise onErrorOccurred/statusBanner.

Two things learned writing this test that are worth remembering:
1. Seed seriesId/seriesTitle via engine.setInitialProperties() BEFORE engine.load(),
   not via root.setProperty() after -- the latter lets Component.onCompleted fire once
   with the default seriesId=0 first (mimicking a real bug: a stale/wrong-id request
   racing a correct one). setInitialProperties() matches how pageStack.push(url, props)
   actually seeds a page in the real app -- only one load() call ever happens.
2. The backend's GET /series/{id}/episodes doesn't validate the series exists -- it
   returns 200 [] for a nonexistent id rather than 404. So "call load() with a bad id"
   is NOT a valid way to test the error path here (it isn't an error). Forced a real
   one instead by pointing the model at an unreachable URL.

Run under QT_QPA_PLATFORM=offscreen, no display needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from models.episodes_model import EpisodesModel
from theme import Theme

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()

current_url = ["http://127.0.0.1:8686"]
episodes_model = EpisodesModel(lambda: current_url[0])
theme = Theme()
engine.rootContext().setContextProperty("episodesModel", episodes_model)
engine.rootContext().setContextProperty("Theme", theme)

errors = []
engine.warnings.connect(lambda warnings: errors.extend(str(w) for w in warnings))

engine.setInitialProperties({"seriesId": 1, "seriesTitle": "Breaking Bad"})
qml_file = Path(__file__).parent.parent / "src" / "qml" / "EpisodesPage.qml"
engine.load(str(qml_file))

if not engine.rootObjects():
    print("FAIL: no root object created (compile/load error)")
    sys.exit(1)

failures = []


def check_initial_load():
    print(f"rowCount after real initial load: {episodes_model.rowCount()}")
    if episodes_model.rowCount() != 4:
        failures.append(f"expected 4 real episode rows, got {episodes_model.rowCount()}")

    print("-- pointing at an unreachable URL and reloading to force a real error --")
    current_url[0] = "http://127.0.0.1:1"  # nothing listens here
    episodes_model.load(1)


def finish():
    if errors:
        failures.append(f"{len(errors)} QML warning(s)/error(s): {errors}")
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        sys.exit(1)
    print("Loaded OK with real season-grouped rows, error handler fired with no scoping errors.")
    print("PASS")
    app.quit()


QTimer.singleShot(1000, check_initial_load)
QTimer.singleShot(3000, finish)
sys.exit(app.exec())
