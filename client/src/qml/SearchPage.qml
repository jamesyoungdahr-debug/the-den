import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "holt"

// Global search results: a responsive poster grid with a type filter.
HoltPage {
    id: page
    objectName: "searchPage"
    title: "Search"
    padding: Theme.space4

    property string typeFilter: "all"

    Connections {
        target: discoverSearchModel
        function onErrorOccurred(message) { banner.showError(message) }
    }

    ColumnLayout {
        width: page.width - 2 * page.padding
        spacing: Theme.space3

        PageHeader {
            title: discoverSearchModel.query.length ? "Results for “" + discoverSearchModel.query + "”" : "Search"
            meta: discoverSearchModel.loading ? "searching…" : discoverSearchModel.count + " results"
            Chip { text: "All"; on: page.typeFilter === "all"; onClicked: page.typeFilter = "all" }
            Chip { text: "Movies"; on: page.typeFilter === "movie"; onClicked: page.typeFilter = "movie" }
            Chip { text: "Series"; on: page.typeFilter === "tv"; onClicked: page.typeFilter = "tv" }
        }

        StatusBanner { id: banner }

        Flow {
            Layout.fillWidth: true
            spacing: Theme.space3
            Repeater {
                model: discoverSearchModel
                delegate: PosterCard {
                    visible: page.typeFilter === "all" || model.mediaType === page.typeFilter
                    posterWidth: Theme.posterLg
                    title: model.title
                    year: model.year
                    posterPath: model.posterPath
                    status: model.status
                    rating: model.rating
                    onClicked: Controls.ApplicationWindow.window.openDetail(model.mediaType, model.tmdbId)
                }
            }
        }

        EmptyState {
            visible: !discoverSearchModel.loading && discoverSearchModel.count === 0
            title: discoverSearchModel.query.length ? "No matches" : "Search for anything"
            body: discoverSearchModel.query.length ? "TMDB found nothing for that. Try another spelling or the original title." : "Movies and series together, straight from TMDB, with what you already have marked."
        }
    }
}
