"""Force-compiles CandidatesPage.qml with candidatesSource overridden to the episode
CandidatesModel (resource="episodes") -- the whole point of generalizing that page in
M5. Loads real candidates for episode 2 (S01E02, still missing).
Run under QT_QPA_PLATFORM=offscreen, no display needed.
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
# Register BOTH -- CandidatesPage.qml's default candidatesSource binds to the global
# "candidatesModel" context property even when we override it via pushed properties,
# so it must exist for the page to compile.
movie_candidates_model = CandidatesModel(lambda: "http://127.0.0.1:8686", resource="movies")
episode_candidates_model = CandidatesModel(lambda: "http://127.0.0.1:8686", resource="episodes")
theme = Theme()
engine.rootContext().setContextProperty("candidatesModel", movie_candidates_model)
engine.rootContext().setContextProperty("episodeCandidatesModel", episode_candidates_model)
engine.rootContext().setContextProperty("Theme", theme)

errors = []
engine.warnings.connect(lambda warnings: errors.extend(str(w) for w in warnings))

qml_file = Path(__file__).parent.parent / "src" / "qml" / "CandidatesPage.qml"
engine.load(str(qml_file))

if not engine.rootObjects():
    print("FAIL: no root object created (compile/load error)")
    sys.exit(1)

root = engine.rootObjects()[0]
root.setProperty("candidatesSource", episode_candidates_model)
root.setProperty("itemId", 2)
root.setProperty("heading", "Breaking Bad S01E02")
episode_candidates_model.load(2)


def finish():
    print(f"episode candidates rowCount: {episode_candidates_model.rowCount()}")
    print(f"movie candidates rowCount (should be untouched, 0): {movie_candidates_model.rowCount()}")
    if episode_candidates_model.rowCount() == 0:
        print("FAIL: expected real episode candidate rows to have loaded")
        sys.exit(1)
    if movie_candidates_model.rowCount() != 0:
        print("FAIL: movie candidates model should not have been touched")
        sys.exit(1)
    if errors:
        print(f"FAIL: {len(errors)} QML warning(s)/error(s): {errors}")
        sys.exit(1)
    print("Loaded OK via the overridden candidatesSource, no scoping errors.")
    print("PASS")
    app.quit()


QTimer.singleShot(1500, finish)
sys.exit(app.exec())
