import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: "Calendar"

    Component.onCompleted: {
        missingMoviesModel.refresh()
        missingEpisodesModel.refresh()
    }

    // No ListView.header involved here (unlike the other pages), so no implicit
    // Component-wrapping id-scoping issue -- these Connections and statusBanner are
    // plain siblings in one ColumnLayout. See ROADMAP.md's "M3" section for why that
    // matters elsewhere in this app.
    Connections {
        target: missingMoviesModel
        function onErrorOccurred(message) {
            statusBanner.text = "Error loading missing movies: " + message
            statusBanner.type = Kirigami.MessageType.Error
            statusBanner.visible = true
        }
    }

    Connections {
        target: missingEpisodesModel
        function onErrorOccurred(message) {
            statusBanner.text = "Error loading missing episodes: " + message
            statusBanner.type = Kirigami.MessageType.Error
            statusBanner.visible = true
        }
    }

    function pad(n) {
        return n < 10 ? "0" + n : String(n)
    }

    ColumnLayout {
        width: page.width
        spacing: Kirigami.Units.largeSpacing

        Kirigami.InlineMessage {
            id: statusBanner
            Layout.fillWidth: true
            visible: false
        }

        Kirigami.Heading {
            text: "Missing movies"
            level: 3
        }

        Repeater {
            id: moviesRepeater
            model: missingMoviesModel
            delegate: RowLayout {
                Layout.fillWidth: true
                Text {
                    text: title
                    font.family: Theme.fontCore
                    font.weight: Font.Bold
                    font.pixelSize: 13
                    color: Theme.ink
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                Text {
                    text: year ? String(year) : "-"
                    font.family: Theme.fontMono
                    font.pixelSize: 10
                    color: Theme.ink42
                }
            }
        }

        Text {
            visible: moviesRepeater.count === 0
            text: "Nothing missing."
            font.family: Theme.fontMono
            font.pixelSize: 11
            color: Theme.ink42
        }

        Kirigami.Separator { Layout.fillWidth: true }

        Kirigami.Heading {
            text: "Upcoming / missing episodes"
            level: 3
        }

        Repeater {
            id: episodesRepeater
            model: missingEpisodesModel
            delegate: RowLayout {
                Layout.fillWidth: true
                Text {
                    text: seriesTitle + " S" + page.pad(seasonNumber) + "E" + page.pad(episodeNumber) + (title ? " — " + title : "")
                    font.family: Theme.fontCore
                    font.weight: Font.Bold
                    font.pixelSize: 13
                    color: Theme.ink
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                Text {
                    text: airDate || "no air date"
                    font.family: Theme.fontMono
                    font.pixelSize: 10
                    color: Theme.ink42
                }
            }
        }

        Text {
            visible: episodesRepeater.count === 0
            text: "Nothing missing."
            font.family: Theme.fontMono
            font.pixelSize: 11
            color: Theme.ink42
        }
    }
}
