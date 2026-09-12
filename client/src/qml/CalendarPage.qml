import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "holt"
import "holt/Holt.js" as H

// Agenda: episodes that have aired but are missing, upcoming episodes, and missing movies.
HoltPage {
    id: page
    objectName: "calendarPage"
    title: "Calendar"
    padding: Theme.space4

    Component.onCompleted: { missingMoviesModel.refresh(); missingEpisodesModel.refresh() }

    Connections { target: missingMoviesModel; function onErrorOccurred(message) { banner.showError("Movies: " + message) } }
    Connections { target: missingEpisodesModel; function onErrorOccurred(message) { banner.showError("Episodes: " + message) } }

    component EpisodeRow: HoltRow {
        required property var model
        thumb: H.posterUrl(model.posterPath)
        thumbWidth: 32
        onClicked: Controls.ApplicationWindow.window.push("EpisodesPage.qml", { seriesId: model.seriesId, seriesTitle: model.seriesTitle, posterPath: model.posterPath })
        RowLayout {
            spacing: 8
            Text { text: model.seriesTitle; font.family: Theme.fontCore; font.pixelSize: 14; font.weight: Font.Bold; color: Theme.ink; elide: Text.ElideRight; Layout.maximumWidth: 360 }
            Text { text: "S" + H.pad(model.seasonNumber) + "E" + H.pad(model.episodeNumber); font.family: Theme.fontMono; font.pixelSize: 11; color: Theme.ink42 }
        }
        Meta { text: (model.title || "TBA") + (model.airDate ? " · " + H.relativeDay(model.airDate) : "") }
        actions: Badge { tone: model.upcoming ? "pending" : "missing"; label: model.upcoming ? "upcoming" : "missing" }
    }

    ColumnLayout {
        width: page.width - 2 * page.padding
        spacing: Theme.space3

        PageHeader { title: "Calendar"; meta: missingEpisodesModel.missingCount + " missing · " + missingEpisodesModel.upcomingCount + " upcoming · " + missingMoviesModel.count + " movies wanted" }
        StatusBanner { id: banner }

        Eyebrow { text: "Aired, still missing"; accent: false; Layout.topMargin: Theme.space2 }
        Repeater { model: missingEpisodesModel; delegate: EpisodeRow { visible: !model.upcoming; Layout.preferredHeight: visible ? implicitHeight : 0 } }
        Meta { visible: !missingEpisodesModel.loading && missingEpisodesModel.missingCount === 0; text: "Nothing missing. Nice." }

        Eyebrow { text: "Upcoming"; accent: false; Layout.topMargin: Theme.space3 }
        Repeater { model: missingEpisodesModel; delegate: EpisodeRow { visible: model.upcoming; Layout.preferredHeight: visible ? implicitHeight : 0 } }
        Meta { visible: !missingEpisodesModel.loading && missingEpisodesModel.upcomingCount === 0; text: "No upcoming episodes for the series you follow." }

        Eyebrow { text: "Movies wanted"; accent: false; Layout.topMargin: Theme.space3 }
        Repeater {
            model: missingMoviesModel
            delegate: HoltRow {
                required property var model
                thumb: H.posterUrl(model.posterPath)
                thumbWidth: 32
                Text { text: model.title; font.family: Theme.fontCore; font.pixelSize: 14; font.weight: Font.Bold; color: Theme.ink; elide: Text.ElideRight; Layout.fillWidth: true }
                Meta { text: model.year ? String(model.year) : "" }
                actions: HoltButton { small: true; text: "Find releases"; onClicked: Controls.ApplicationWindow.window.push("CandidatesPage.qml", { itemId: model.movieId, heading: model.title }) }
            }
        }
        Meta { visible: !missingMoviesModel.loading && missingMoviesModel.count === 0; text: "Every movie in the library is on disk." }
    }
}
