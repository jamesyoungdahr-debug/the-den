"""Force-compiles CandidatesPage.qml against real CandidatesModel + backend data (see
check_candidates_model.py for the fixture setup this assumes is already running/seeded).
Loading real rows here is what actually exercises the delegate's per-row bindings
(isBest accent, StatusPill, seeders null-check) -- an empty list wouldn't instantiate
the delegate at all. Run under QT_QPA_PLATFORM=offscreen, no display needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from models.candidates_model import CandidatesModel
from theme import Theme

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
candidates_model = CandidatesModel(lambda: "http://127.0.0.1:8686")
theme = Theme()
engine.rootContext().setContextProperty("candidatesModel", candidates_model)
engine.rootContext().setContextProperty("Theme", theme)

errors = []
engine.warnings.connect(lambda warnings: errors.extend(str(w) for w in warnings))

qml_file = Path(__file__).parent.parent / "src" / "qml" / "CandidatesPage.qml"
engine.load(str(qml_file))

if not engine.rootObjects():
    print("FAIL: no root object created (compile/load error)")
    sys.exit(1)

root = engine.rootObjects()[0]
root.setProperty("movieId", 1)
root.setProperty("movieTitle", "Inception")
candidates_model.load(1)  # movieId=1 as a property doesn't retrigger Component.onCompleted


def finish():
    print(f"rowCount after load: {candidates_model.rowCount()}")
    if candidates_model.rowCount() == 0:
        print("FAIL: expected real candidate rows to have loaded (delegate never instantiated)")
        sys.exit(1)
    if errors:
        print(f"FAIL: {len(errors)} QML warning(s)/error(s): {errors}")
        sys.exit(1)
    print(f"Loaded OK with {candidates_model.rowCount()} real row(s) through the delegate. QML warnings: none")
    print("PASS")
    app.quit()


QTimer.singleShot(1500, finish)
sys.exit(app.exec())
