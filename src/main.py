import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from api_client import ApiClient
from models.candidates_model import CandidatesModel
from models.indexer_model import IndexerListModel
from models.movie_model import MovieListModel, MovieSearchResultsModel
from theme import Theme


def main() -> None:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("The Den")
    app.setOrganizationName("the-den")

    engine = QQmlApplicationEngine()
    api_client = ApiClient()
    indexer_model = IndexerListModel(lambda: api_client.baseUrl)
    movie_model = MovieListModel(lambda: api_client.baseUrl)
    movie_search_model = MovieSearchResultsModel(lambda: api_client.baseUrl)
    candidates_model = CandidatesModel(lambda: api_client.baseUrl)
    theme = Theme()
    engine.rootContext().setContextProperty("apiClient", api_client)
    engine.rootContext().setContextProperty("indexerModel", indexer_model)
    engine.rootContext().setContextProperty("movieModel", movie_model)
    engine.rootContext().setContextProperty("movieSearchModel", movie_search_model)
    engine.rootContext().setContextProperty("candidatesModel", candidates_model)
    engine.rootContext().setContextProperty("Theme", theme)

    qml_file = Path(__file__).parent / "qml" / "Main.qml"
    engine.load(str(qml_file))

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
