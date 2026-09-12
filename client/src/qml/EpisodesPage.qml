import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "holt"
import "holt/Holt.js" as H

// One series: poster header with progress, then episode rows grouped by season.
HoltPage {
    id: page
    objectName: "episodesPage"
    property int seriesId: 0
    property string seriesTitle: ""
    property string posterPath: ""
    title: seriesTitle
    padding: Theme.space4

    Component.onCompleted: episodesModel.load(seriesId)

    Connections {
        target: episodesModel
        function onErrorOccurred(message) { banner.showError(message) }
    }

    ColumnLayout {
        width: page.width - 2 * page.padding
        spacing: Theme.space3

        RowLayout {
            spacing: Theme.space4
            Rectangle {
                visible: page.posterPath !== ""
                width: 96; height: 144; radius: Theme.radiusMd; color: Theme.raised; clip: true
                Image { anchors.fill: parent; source: H.posterUrl(page.posterPath); fillMode: Image.PreserveAspectCrop; asynchronous: true; sourceSize.width: 342 }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6
                Eyebrow { text: "Series" }
                Text { text: page.seriesTitle; font.family: Theme.fontCore; font.pixelSize: Theme.sizePageTitle; font.weight: Font.ExtraBold; font.letterSpacing: -1; color: Theme.ink; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Meta { text: episodesModel.haveCount + " of " + episodesModel.count + " episodes" }
                ProgressBar { Layout.fillWidth: true; Layout.maximumWidth: 320; value: episodesModel.count ? episodesModel.haveCount / episodesModel.count : 0; tone: "available" }
            }
        }

        StatusBanner { id: banner }

        ListView {
            id: list
            Layout.fillWidth: true
            implicitHeight: contentHeight
            interactive: false
            model: episodesModel
            spacing: 6
            section.property: "seasonNumber"
            section.criteria: ViewSection.FullString
            section.delegate: Eyebrow { text: "Season " + H.pad(Number(section)); accent: false; topPadding: Theme.space3; bottomPadding: 6 }

            delegate: HoltRow {
                required property var model
                width: list.width
                thumbWidth: 0
                RowLayout {
                    spacing: 10
                    Text { text: "E" + H.pad(model.episodeNumber); font.family: Theme.fontMono; font.pixelSize: 11; color: Theme.ink42 }
                    Text { text: model.title || "TBA"; font.family: Theme.fontCore; font.pixelSize: 14; font.weight: Font.Bold; color: Theme.ink; elide: Text.ElideRight; Layout.fillWidth: true }
                }
                Meta { text: model.airDate ? "aired " + model.airDate : "no air date" }
                actions: [
                    Badge { tone: model.hasFile ? "available" : "missing"; label: model.hasFile ? "have" : "missing" },
                    HoltButton { visible: !model.hasFile; small: true; text: "Find releases"; onClicked: Controls.ApplicationWindow.window.push("CandidatesPage.qml", { candidatesSource: episodeCandidatesModel, itemId: model.episodeId, heading: page.seriesTitle + " S" + H.pad(model.seasonNumber) + "E" + H.pad(model.episodeNumber) }) }
                ]
            }
        }

        EmptyState { visible: !episodesModel.loading && episodesModel.count === 0; title: "No episodes"; body: "TVmaze hasn't listed any episodes for this series yet." }
    }
}
