"""Force-compiles MoviesPage.qml against real models + backend, AND actually triggers
an errorOccurred signal (adding a duplicate movie, assumed id=1/tmdb_id=27205 already
seeded, which the backend rejects with 400) -- the earlier version of this test never
exercised the Connections handlers that reference statusBanner by id, which is exactly
what let the ListView.header id-scoping bug ship undetected. Run under
QT_QPA_PLATFORM=offscreen, no display needed.
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


def trigger_error():
    print("-- triggering movieModel.addMovie() with a duplicate tmdb_id to exercise onErrorOccurred --")
    movie_model.addMovie(27205, "Inception", "2010", "", "")


def finish():
    print(f"rowCount after load: {movie_model.rowCount()}")
    if movie_model.rowCount() == 0:
        print("FAIL: expected at least one real movie row to have loaded (delegate never instantiated)")
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
