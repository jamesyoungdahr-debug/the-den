import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from api_client import ApiClient
from models.calendar_model import CalendarEpisodesModel, CalendarMoviesModel
from models.candidates_model import CandidatesModel
from models.discover_model import DetailController, DiscoverSearchModel, RailModel
from models.episodes_model import EpisodesModel
from models.indexer_model import IndexerListModel
from models.movie_model import MovieListModel, MovieSearchResultsModel
from models.requests_model import RequestsModel
from models.series_model import SeriesListModel, SeriesSearchResultsModel
from models.settings_controller import SettingsController
from models.torrents_model import TorrentsModel
from theme import Theme

RAILS = ("trending", "popular-movies", "upcoming-movies", "popular-tv", "on-the-air", "recommended")


def build_context(api: ApiClient) -> dict:
    """Every object QML can reach by name. Shared with the headless tests so a page
    compiles against exactly what the app gives it."""
    ctx = {
        "apiClient": api,
        "Theme": Theme(),
        "indexerModel": IndexerListModel(api),
        "movieModel": MovieListModel(api),
        "movieSearchModel": MovieSearchResultsModel(api),
        "candidatesModel": CandidatesModel(api, resource="movies"),
        "torrentsModel": TorrentsModel(api),
        "seriesModel": SeriesListModel(api),
        "seriesSearchModel": SeriesSearchResultsModel(api),
        "episodesModel": EpisodesModel(api),
        "episodeCandidatesModel": CandidatesModel(api, resource="episodes"),
        "missingMoviesModel": CalendarMoviesModel(api),
        "missingEpisodesModel": CalendarEpisodesModel(api),
        "settingsController": SettingsController(api),
        "discoverSearchModel": DiscoverSearchModel(api),
        "detailController": DetailController(api),
        "requestsModel": RequestsModel(api),
    }
    for rail in RAILS:
        # trending -> trendingRail, popular-movies -> popularMoviesRail
        parts = rail.split("-")
        name = parts[0] + "".join(p.capitalize() for p in parts[1:]) + "Rail"
        ctx[name] = RailModel(api, rail)
    return ctx


def main() -> None:
    # Kirigami's desktop style unless the launcher/user picked one already.
    if not os.environ.get("QT_QUICK_CONTROLS_STYLE"):
        QQuickStyle.setStyle("org.kde.desktop")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("The Den")
    app.setOrganizationName("the-den")
    app.setDesktopFileName("the-den-client")
    logo = Path(__file__).resolve().parents[1] / "assets" / "logo.svg"
    if logo.exists():
        app.setWindowIcon(QIcon(str(logo)))

    engine = QQmlApplicationEngine()
    api = ApiClient()
    context = build_context(api)
    for name, obj in context.items():
        engine.rootContext().setContextProperty(name, obj)

    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "qml" / "Main.qml")))
    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
