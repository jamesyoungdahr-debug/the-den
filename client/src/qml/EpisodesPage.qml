import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: seriesTitle

    property int seriesId: 0
    property string seriesTitle: ""

    Component.onCompleted: episodesModel.load(seriesId)

    function pad(n) {
        return n < 10 ? "0" + n : String(n)
    }

    ListView {
        id: listView
        model: episodesModel

        section.property: "seasonNumber"
        section.criteria: ViewSection.FullString
        section.delegate: Kirigami.ListSectionHeader {
            width: ListView.view.width
            text: "Season " + page.pad(Number(section))
        }

        header: ColumnLayout {
            width: ListView.view.width
            spacing: Kirigami.Units.largeSpacing

            // Nested here, not as a page-level sibling: ListView.header is
            // Component-typed, so an inline item assigned to it gets implicitly
            // wrapped in its own Component with its own id scope -- statusBanner
            // is only visible to things declared inside that same wrapped scope.
            Connections {
                target: episodesModel
                function onErrorOccurred(message) {
                    statusBanner.text = "Error: " + message
                    statusBanner.type = Kirigami.MessageType.Error
                    statusBanner.visible = true
                }
            }

            Kirigami.InlineMessage {
                id: statusBanner
                Layout.fillWidth: true
                visible: false
            }
        }

        delegate: Kirigami.SwipeListItem {
            width: ListView.view.width
            contentItem: RowLayout {
                spacing: Kirigami.Units.largeSpacing

                Text {
                    text: "E" + page.pad(episodeNumber) + (title ? " — " + title : "")
                    font.family: Theme.fontCore
                    font.weight: Font.Bold
                    font.pixelSize: 13
                    color: Theme.ink
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                StatusPill {
                    label: hasFile ? "have" : "missing"
                    tone: hasFile ? "healthy" : "idle"
                }
            }
            actions: [
                Kirigami.Action {
                    text: "Find releases"
                    visible: !hasFile
                    onTriggered: applicationWindow().pageStack.push(
                        Qt.resolvedUrl("CandidatesPage.qml"),
                        {
                            candidatesSource: episodeCandidatesModel,
                            itemId: episodeId,
                            heading: page.seriesTitle + " S" + page.pad(seasonNumber) + "E" + page.pad(episodeNumber)
                        })
                }
            ]
        }
    }
}
