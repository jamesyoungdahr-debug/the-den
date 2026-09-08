"""Force-compiles MoviesPage.qml against real MovieListModel/MovieSearchResultsModel +
backend. Run under QT_QPA_PLATFORM=offscreen, no display needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from models.movie_model import MovieListModel, MovieSearchResultsModel
from theme import Theme

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
movie_model = MovieListModel(lambda: "http://127.0.0.1:8686")
movie_search_model = MovieSearchResultsModel(lambda: "http://127.0.0.1:8686")
theme = Theme()
engine.rootContext().setContextProperty("movieModel", movie_model)
engine.rootContext().setContextProperty("movieSearchModel", movie_search_model)
engine.rootContext().setContextProperty("Theme", theme)

errors = []
engine.warnings.connect(lambda warnings: errors.extend(str(w) for w in warnings))

qml_file = Path(__file__).parent.parent / "src" / "qml" / "MoviesPage.qml"
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


QTimer.singleShot(1500, finish)
sys.exit(app.exec())
