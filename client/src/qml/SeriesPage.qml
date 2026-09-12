import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "holt"

// The TV library as a poster grid; click through to episodes; add via TVmaze search.
HoltPage {
    id: page
    objectName: "seriesPage"
    title: "TV"
    padding: Theme.space4

    Component.onCompleted: {
        seriesModel.refresh()
        if (apiClient.isAdmin) Controls.ApplicationWindow.window.pageAction = { text: "Add series", trigger: function () { addDialog.open() } }
    }
    Controls.StackView.onDeactivated: Controls.ApplicationWindow.window.pageAction = null
    Controls.StackView.onActivated: if (apiClient.isAdmin) Controls.ApplicationWindow.window.pageAction = { text: "Add series", trigger: function () { addDialog.open() } }

    Connections {
        target: seriesModel
        function onErrorOccurred(message) { banner.showError(message) }
    }
    Connections {
        target: seriesSearchModel
        function onErrorOccurred(message) { banner.showError("Search error: " + message) }
    }

    ColumnLayout {
        width: page.width - 2 * page.padding
        spacing: Theme.space3

        PageHeader { title: "TV"; meta: seriesModel.count + " series in the library" }
        StatusBanner { id: banner }

        Flow {
            Layout.fillWidth: true
            spacing: Theme.space3
            Repeater {
                model: seriesModel
                delegate: PosterCard {
                    posterWidth: Theme.posterLg
                    title: model.title
                    year: model.year
                    posterPath: model.posterPath
                    status: ""
                    showRating: false
                    onClicked: Controls.ApplicationWindow.window.push("EpisodesPage.qml", { seriesId: model.seriesId, seriesTitle: model.title, posterPath: model.posterPath })
                    HoltButton { visible: apiClient.isAdmin; anchors { right: parent.right; rightMargin: 6 } y: Math.round(parent.posterWidth * 1.5) - height - 6; small: true; kind: "quiet"; text: "✕"; onClicked: seriesModel.deleteSeries(model.seriesId) }
                }
            }
        }

        EmptyState {
            visible: !seriesModel.loading && seriesModel.count === 0
            title: "No series yet"
            body: apiClient.isAdmin ? "Add one here or from Discover; episode lists come from TVmaze." : "Request a series on Discover and it'll show up here once approved."
            actionText: "Discover"
            onAction: Controls.ApplicationWindow.window.navigate("discover")
        }
    }

    HoltDialog {
        id: addDialog
        title: "Add a series"
        onClosed: { seriesSearchModel.clear(); searchField.text = "" }
        RowLayout {
            Layout.fillWidth: true
            HoltTextField { id: searchField; Layout.fillWidth: true; placeholderText: "Search TVmaze…"; onAccepted: seriesSearchModel.search(text) }
            HoltButton { text: "Search"; onClicked: seriesSearchModel.search(searchField.text) }
        }
        Repeater {
            model: seriesSearchModel
            delegate: HoltRow {
                required property var model
                Text { text: model.title; font.family: Theme.fontCore; font.pixelSize: 13; font.weight: Font.Bold; color: Theme.ink; elide: Text.ElideRight; Layout.fillWidth: true }
                Meta { text: model.year ? String(model.year) : "" }
                actions: HoltButton { kind: "primary"; small: true; text: "Add"; onClicked: { seriesModel.addSeries(model.tvmazeId, model.title, model.year ? String(model.year) : "", model.overview, model.posterPath); addDialog.close() } }
            }
        }
        footer: HoltButton { kind: "quiet"; text: "Close"; onClicked: addDialog.close() }
    }
}
