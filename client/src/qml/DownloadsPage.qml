import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: "Downloads"

    Component.onCompleted: downloadsModel.refresh()

    readonly property var toneMap: ({
        queued: "working",
        downloading: "working",
        completed: "idle",
        imported: "healthy",
        failed: "warning",
    })

    ListView {
        id: listView
        model: downloadsModel

        header: ColumnLayout {
            width: ListView.view.width
            spacing: Kirigami.Units.largeSpacing

            // Nested here, not as a page-level sibling: ListView.header is
            // Component-typed, so an inline item assigned to it gets implicitly
            // wrapped in its own Component with its own id scope -- statusBanner
            // is only visible to things declared inside that same wrapped scope.
            // (See ROADMAP.md's "M3" section for the bug this pattern avoids.)
            Connections {
                target: downloadsModel
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
                    text: releaseTitle
                    font.family: Theme.fontCore
                    font.weight: Font.Bold
                    font.pixelSize: 13
                    color: Theme.ink
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                StatusPill {
                    label: status
                    tone: page.toneMap[status] || "idle"
                }

                Controls.Button {
                    text: "Check now"
                    visible: status !== "imported"
                    onClicked: downloadsModel.check(downloadId)
                }
            }
        }
    }
}
