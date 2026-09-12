import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "holt"

// The movie library as a poster grid with have/wanted badges; add via a TMDB search
// dialog (the top bar's primary action), remove for admins.
HoltPage {
    id: page
    objectName: "moviesPage"
    title: "Movies"
    padding: Theme.space4

    property string filter: "all"   // all | missing | have

    Component.onCompleted: {
        movieModel.refresh()
        if (apiClient.isAdmin) Controls.ApplicationWindow.window.pageAction = { text: "Add movie", trigger: function () { addDialog.open() } }
    }
    Controls.StackView.onDeactivated: Controls.ApplicationWindow.window.pageAction = null
    Controls.StackView.onActivated: if (apiClient.isAdmin) Controls.ApplicationWindow.window.pageAction = { text: "Add movie", trigger: function () { addDialog.open() } }

    Connections {
        target: movieModel
        function onErrorOccurred(message) { banner.showError(message) }
    }
    Connections {
        target: movieSearchModel
        function onErrorOccurred(message) { banner.showError("Search error: " + message) }
    }

    ColumnLayout {
        width: page.width - 2 * page.padding
        spacing: Theme.space3

        PageHeader {
            title: "Movies"
            meta: movieModel.count + " in the library"
            Chip { text: "All"; on: page.filter === "all"; onClicked: page.filter = "all" }
            Chip { text: "Wanted"; on: page.filter === "missing"; onClicked: page.filter = "missing" }
            Chip { text: "Have"; on: page.filter === "have"; onClicked: page.filter = "have" }
        }

        StatusBanner { id: banner }

        Flow {
            Layout.fillWidth: true
            spacing: Theme.space3
            Repeater {
                model: movieModel
                delegate: PosterCard {
                    visible: page.filter === "all" || (page.filter === "have") === model.hasFile
                    posterWidth: Theme.posterLg
                    title: model.title
                    year: model.year
                    posterPath: model.posterPath
                    status: model.hasFile ? "available" : "wanted"
                    showRating: false
                    onClicked: Controls.ApplicationWindow.window.openDetail("movie", model.tmdbId)

                    Row {
                        // bottom-right of the poster, clear of the status badge
                        anchors { right: parent.right; rightMargin: 6 }
                        y: Math.round(parent.posterWidth * 1.5) - height - 6
                        spacing: 4
                        HoltButton { visible: !model.hasFile; small: true; text: "Releases"; onClicked: Controls.ApplicationWindow.window.push("CandidatesPage.qml", { itemId: model.movieId, heading: model.title }) }
                        HoltButton { visible: apiClient.isAdmin; small: true; kind: "quiet"; text: "✕"; onClicked: movieModel.deleteMovie(model.movieId) }
                    }
                }
            }
        }

        EmptyState {
            visible: !movieModel.loading && movieModel.count === 0
            title: "No movies yet"
            body: apiClient.isAdmin ? "Add one here or from Discover; automation looks for it on your indexers." : "Ask for something on Discover and it'll show up here once approved."
            actionText: "Discover"
            onAction: Controls.ApplicationWindow.window.navigate("discover")
        }
    }

    HoltDialog {
        id: addDialog
        title: "Add a movie"
        onClosed: { movieSearchModel.clear(); searchField.text = "" }
        RowLayout {
            Layout.fillWidth: true
            HoltTextField { id: searchField; Layout.fillWidth: true; placeholderText: "Search TMDB…"; onAccepted: movieSearchModel.search(text) }
            HoltButton { text: "Search"; onClicked: movieSearchModel.search(searchField.text) }
        }
        Repeater {
            model: movieSearchModel
            delegate: HoltRow {
                required property var model
                Text { text: model.title; font.family: Theme.fontCore; font.pixelSize: 13; font.weight: Font.Bold; color: Theme.ink; elide: Text.ElideRight; Layout.fillWidth: true }
                Meta { text: model.year ? String(model.year) : "" }
                actions: HoltButton { kind: "primary"; small: true; text: "Add"; onClicked: { movieModel.addMovie(model.tmdbId, model.title, model.year ? String(model.year) : "", model.overview, model.posterPath); addDialog.close() } }
            }
        }
        footer: HoltButton { kind: "quiet"; text: "Close"; onClicked: addDialog.close() }
    }
}
