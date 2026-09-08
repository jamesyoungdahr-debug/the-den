import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: "Releases"

    // Movies push this page with just itemId/heading, taking the default
    // candidatesSource (the movie CandidatesModel). Episodes override
    // candidatesSource to the episode CandidatesModel at push time -- same page,
    // same underlying model class, different backend resource ("movies" vs
    // "episodes"), see src/models/candidates_model.py.
    property var candidatesSource: candidatesModel
    property int itemId: 0
    property string heading: ""

    Component.onCompleted: candidatesSource.load(itemId)

    ListView {
        id: listView
        model: page.candidatesSource

        header: ColumnLayout {
            width: ListView.view.width
            spacing: Kirigami.Units.largeSpacing

            // Nested here, not as a page-level sibling: ListView.header is
            // Component-typed, so an inline item assigned to it gets implicitly
            // wrapped in its own Component with its own id scope -- statusBanner
            // is only visible to things declared inside that same wrapped scope.
            Connections {
                target: page.candidatesSource
                function onErrorOccurred(message) {
                    statusBanner.text = "Error: " + message
                    statusBanner.type = Kirigami.MessageType.Error
                    statusBanner.visible = true
                }
                function onGrabFinished(ok, message) {
                    statusBanner.text = ok ? "Grabbed — check Downloads" : "Grab failed: " + message
                    statusBanner.type = ok ? Kirigami.MessageType.Positive : Kirigami.MessageType.Warning
                    statusBanner.visible = true
                }
            }

            Kirigami.Heading {
                text: page.heading
                level: 2
                Layout.fillWidth: true
                elide: Text.ElideRight
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

                Rectangle {
                    visible: isBest
                    width: 4
                    Layout.fillHeight: true
                    color: Theme.current
                    radius: 2
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: title
                        font.family: Theme.fontCore
                        font.weight: Font.Bold
                        font.pixelSize: 13
                        color: Theme.ink
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    Text {
                        text: indexerName + " — " + quality + " — " + (seeders !== null && seeders !== undefined ? seeders : "-") + " seeders"
                        font.family: Theme.fontMono
                        font.pixelSize: 10
                        color: Theme.ink42
                    }
                }

                StatusPill {
                    visible: isBest
                    label: "best match"
                    tone: "healthy"
                }

                Controls.Button {
                    text: "Grab"
                    highlighted: true
                    onClicked: page.candidatesSource.grab(downloadUrl, title)
                }
            }
        }
    }
}
