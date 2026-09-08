import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from api_client import ApiClient
from models.calendar_model import CalendarEpisodesModel, CalendarMoviesModel
from models.candidates_model import CandidatesModel
from models.downloads_model import DownloadsModel
from models.episodes_model import EpisodesModel
from models.indexer_model import IndexerListModel
from models.movie_model import MovieListModel, MovieSearchResultsModel
from models.series_model import SeriesListModel, SeriesSearchResultsModel
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
    candidates_model = CandidatesModel(lambda: api_client.baseUrl, resource="movies")
    downloads_model = DownloadsModel(lambda: api_client.baseUrl)
    series_model = SeriesListModel(lambda: api_client.baseUrl)
    series_search_model = SeriesSearchResultsModel(lambda: api_client.baseUrl)
    episodes_model = EpisodesModel(lambda: api_client.baseUrl)
    episode_candidates_model = CandidatesModel(lambda: api_client.baseUrl, resource="episodes")
    missing_movies_model = CalendarMoviesModel(lambda: api_client.baseUrl)
    missing_episodes_model = CalendarEpisodesModel(lambda: api_client.baseUrl)
    theme = Theme()
    engine.rootContext().setContextProperty("apiClient", api_client)
    engine.rootContext().setContextProperty("indexerModel", indexer_model)
    engine.rootContext().setContextProperty("movieModel", movie_model)
    engine.rootContext().setContextProperty("movieSearchModel", movie_search_model)
    engine.rootContext().setContextProperty("candidatesModel", candidates_model)
    engine.rootContext().setContextProperty("downloadsModel", downloads_model)
    engine.rootContext().setContextProperty("seriesModel", series_model)
    engine.rootContext().setContextProperty("seriesSearchModel", series_search_model)
    engine.rootContext().setContextProperty("episodesModel", episodes_model)
    engine.rootContext().setContextProperty("episodeCandidatesModel", episode_candidates_model)
    engine.rootContext().setContextProperty("missingMoviesModel", missing_movies_model)
    engine.rootContext().setContextProperty("missingEpisodesModel", missing_episodes_model)
    engine.rootContext().setContextProperty("Theme", theme)

    qml_file = Path(__file__).parent / "qml" / "Main.qml"
    engine.load(str(qml_file))

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
