import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "holt"
import "holt/Holt.js" as H

// Scored releases for one movie or episode; Grab sends one to the built-in client.
HoltPage {
    id: page
    objectName: "candidatesPage"
    property var candidatesSource: candidatesModel
    property int itemId: 0
    property string heading: ""
    title: "Releases"
    padding: Theme.space4

    Component.onCompleted: candidatesSource.load(itemId)

    Connections {
        target: page.candidatesSource
        function onErrorOccurred(message) { banner.showError(message) }
        function onGrabFinished(itemId, ok, message) {
            if (itemId !== page.itemId) return
            banner.show(ok ? "Grabbed — watch it on Downloads" : "Grab failed: " + message, ok ? "positive" : "error")
            if (ok) Controls.ApplicationWindow.window.toast("Grabbed " + page.heading, "positive")
        }
    }

    ColumnLayout {
        width: page.width - 2 * page.padding
        spacing: Theme.space3

        PageHeader { title: page.heading; meta: page.candidatesSource.loading ? "searching your indexers…" : page.candidatesSource.count + " releases, best match first" }
        StatusBanner { id: banner }

        Repeater {
            model: page.candidatesSource
            delegate: HoltRow {
                required property var model
                thumbWidth: 0
                highlighted: model.isBest
                RowLayout {
                    spacing: 8
                    Rectangle { visible: model.isBest; width: 3; height: 16; radius: 1; color: Theme.current }
                    Text { text: model.title; font.family: Theme.fontCore; font.pixelSize: 13; font.weight: Font.Bold; color: Theme.ink; elide: Text.ElideMiddle; Layout.fillWidth: true }
                }
                Meta { text: model.indexerName + " · " + (model.size ? H.bytes(model.size) + " · " : "") + model.seeders + " seeders · " + model.peers + " peers" }
                actions: [
                    Chip { text: model.quality; enabled: false; implicitHeight: 24 },
                    Badge { visible: model.isBest; tone: "available"; label: "best match" },
                    HoltButton { kind: model.isBest ? "primary" : "secondary"; small: true; text: "Grab"; onClicked: page.candidatesSource.grab(model.downloadUrl, model.title) }
                ]
            }
        }

        Repeater { model: page.candidatesSource.loading && page.candidatesSource.count === 0 ? 4 : 0; delegate: Skeleton { Layout.fillWidth: true; height: 64 } }

        EmptyState {
            visible: !page.candidatesSource.loading && page.candidatesSource.count === 0
            title: "No releases found"
            body: "None of your enabled indexers returned anything for this. Automation keeps trying every cycle."
        }
    }
}
