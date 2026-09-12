import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "holt"
import "holt/Holt.js" as H

// The built-in torrent client, live: engine header, then rows grouped Active /
// Seeding / Stopped with drawn progress bars and pause / resume / remove. Polls
// while this page is on screen.
HoltPage {
    id: page
    objectName: "downloadsPage"
    title: "Downloads"
    padding: Theme.space4

    Component.onCompleted: {
        torrentsModel.polling = true
        Controls.ApplicationWindow.window.pageAction = { text: "Add torrent", trigger: function () { addDialog.open() } }
    }
    Component.onDestruction: torrentsModel.polling = false
    Controls.StackView.onDeactivated: { torrentsModel.polling = false; Controls.ApplicationWindow.window.pageAction = null }
    Controls.StackView.onActivated: { torrentsModel.polling = true; Controls.ApplicationWindow.window.pageAction = { text: "Add torrent", trigger: function () { addDialog.open() } } }

    Connections {
        target: torrentsModel
        function onErrorOccurred(message) { banner.showError(message) }
        function onAddFinished(ok, message) { Controls.ApplicationWindow.window.toast(message, ok ? "positive" : "error"); if (!ok) banner.showError(message) }
    }

    component Stat: ColumnLayout {
        property string label: ""
        property string value: ""
        spacing: 2
        Text { text: value; font.family: Theme.fontCore; font.pixelSize: 20; font.weight: Font.ExtraBold; font.letterSpacing: -0.6; color: Theme.ink }
        Eyebrow { text: label; accent: false }
    }

    component Group: ColumnLayout {
        property string name: ""
        property string groupKey: ""
        spacing: 6
        Layout.fillWidth: true
        visible: count > 0
        property int count: 0
        Eyebrow { text: name + " · " + count; accent: false; Layout.topMargin: Theme.space2 }
        Repeater {
            model: torrentsModel
            delegate: HoltRow {
                required property var model
                visible: model.group === groupKey
                Layout.preferredHeight: visible ? implicitHeight : 0
                thumbWidth: 0
                Component.onCompleted: if (visible) count++
                RowLayout {
                    spacing: 8
                    Text { text: model.label || model.name; font.family: Theme.fontCore; font.pixelSize: 14; font.weight: Font.Bold; color: Theme.ink; elide: Text.ElideMiddle; Layout.fillWidth: true }
                }
                Meta { visible: model.label !== ""; text: model.name; Layout.fillWidth: true }
                ProgressBar { Layout.fillWidth: true; Layout.topMargin: 4; value: model.progress; tone: model.group === "seeding" ? "available" : "processing" }
                Meta {
                    Layout.fillWidth: true
                    text: model.error ? model.error : (Math.round(model.progress * 100) + "% of " + H.bytes(model.totalSize)
                        + (model.group === "active" ? " · ↓ " + H.rate(model.downloadRate) + " · eta " + H.eta(model.etaSeconds) : "")
                        + " · ↑ " + H.rate(model.uploadRate) + " · ratio " + Number(model.ratio).toFixed(2)
                        + " · " + model.numSeeds + " seeds / " + model.numPeers + " peers")
                }
                actions: [
                    Badge { tone: H.torrentBadge(model).tone; label: H.torrentBadge(model).label },
                    HoltButton { visible: model.group !== "stopped"; kind: "quiet"; small: true; text: "Pause"; onClicked: torrentsModel.pause(model.infoHash) },
                    HoltButton { visible: model.group === "stopped"; kind: "quiet"; small: true; text: "Resume"; onClicked: torrentsModel.resume(model.infoHash) },
                    HoltButton { kind: "quiet"; small: true; text: "Remove"; onClicked: { removeDialog.infoHash = model.infoHash; removeDialog.name = model.label || model.name; removeDialog.open() } }
                ]
            }
        }
    }

    ColumnLayout {
        width: page.width - 2 * page.padding
        spacing: Theme.space3

        PageHeader { title: "Downloads"; meta: "built-in torrent client" }
        StatusBanner { id: banner }

        GlassPanel {
            Layout.fillWidth: true
            RowLayout {
                width: parent.width
                spacing: Theme.space5
                Stat { label: "Down"; value: H.rate(torrentsModel.downloadRate) }
                Stat { label: "Up"; value: H.rate(torrentsModel.uploadRate) }
                Stat { label: "Active"; value: String(torrentsModel.activeCount) }
                Stat { label: "Seeding"; value: String(torrentsModel.seedingCount) }
                Item { Layout.fillWidth: true }
                ColumnLayout {
                    spacing: 4
                    Badge { tone: torrentsModel.engine.running ? "available" : "error"; label: torrentsModel.engine.running ? "engine up" : "engine down" }
                    Meta { text: torrentsModel.engine.running ? "port " + torrentsModel.engine.listen_port + " · DHT " + (torrentsModel.engine.dht_running ? "on" : "off") : "" }
                }
            }
        }

        Group { name: "Active"; groupKey: "active"; count: torrentsModel.activeCount }
        Group { name: "Seeding"; groupKey: "seeding"; count: torrentsModel.seedingCount }
        Group { name: "Stopped"; groupKey: "stopped"; count: torrentsModel.count - torrentsModel.activeCount - torrentsModel.seedingCount }

        EmptyState {
            visible: !torrentsModel.loading && torrentsModel.count === 0
            title: "Nothing downloading"
            body: "Grabs from Releases land here, or add a magnet link by hand."
            actionText: "Add torrent"
            onAction: addDialog.open()
        }
    }

    HoltDialog {
        id: addDialog
        title: "Add a torrent"
        Field { label: "Magnet link, .torrent URL, or path on the server"; HoltTextField { id: sourceField; placeholderText: "magnet:?xt=urn:btih:…"; onAccepted: { torrentsModel.add(text); text = ""; addDialog.close() } } }
        footer: [
            HoltButton { kind: "quiet"; text: "Cancel"; onClicked: addDialog.close() },
            HoltButton { kind: "primary"; text: "Add"; enabled: sourceField.text.trim().length > 0; onClicked: { torrentsModel.add(sourceField.text); sourceField.text = ""; addDialog.close() } }
        ]
    }

    HoltDialog {
        id: removeDialog
        property string infoHash: ""
        property string name: ""
        title: "Remove " + name
        Text { text: "Remove it from the client, or also delete the downloaded files? Anything already imported into the library stays."; font.family: Theme.fontCore; font.pixelSize: 13; color: Theme.ink70; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        footer: [
            HoltButton { kind: "quiet"; text: "Cancel"; onClicked: removeDialog.close() },
            HoltButton { text: "Remove"; onClicked: { torrentsModel.remove(removeDialog.infoHash, false); removeDialog.close() } },
            HoltButton { kind: "danger"; text: "Remove + delete files"; onClicked: { torrentsModel.remove(removeDialog.infoHash, true); removeDialog.close() } }
        ]
    }
}
