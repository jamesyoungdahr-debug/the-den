import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from api_client import ApiClient
from models.indexer_model import IndexerListModel


def main() -> None:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("The Den")
    app.setOrganizationName("the-den")

    engine = QQmlApplicationEngine()
    api_client = ApiClient()
    indexer_model = IndexerListModel(lambda: api_client.baseUrl)
    engine.rootContext().setContextProperty("apiClient", api_client)
    engine.rootContext().setContextProperty("indexerModel", indexer_model)

    qml_file = Path(__file__).parent / "qml" / "Main.qml"
    engine.load(str(qml_file))

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
