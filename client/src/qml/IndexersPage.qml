import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "holt"

// Indexers: one row each with test / delete; the add form lives in a dialog.
HoltPage {
    id: page
    objectName: "indexersPage"
    title: "Indexers"
    padding: Theme.space4

    Component.onCompleted: {
        indexerModel.refresh()
        Controls.ApplicationWindow.window.pageAction = { text: "Add indexer", trigger: function () { addDialog.open() } }
    }
    Controls.StackView.onDeactivated: Controls.ApplicationWindow.window.pageAction = null
    Controls.StackView.onActivated: Controls.ApplicationWindow.window.pageAction = { text: "Add indexer", trigger: function () { addDialog.open() } }

    property var testResults: ({})

    Connections {
        target: indexerModel
        function onErrorOccurred(message) { banner.showError(message) }
        function onTestResult(indexerId, ok, message) {
            var r = page.testResults; r[indexerId] = { ok: ok, message: message }; page.testResults = r
            banner.show((ok ? "Test OK: " : "Test failed: ") + message, ok ? "positive" : "warning")
        }
    }

    ColumnLayout {
        width: page.width - 2 * page.padding
        spacing: Theme.space3

        PageHeader { title: "Indexers"; meta: indexerModel.count + " configured · Torznab and Newznab" }
        StatusBanner { id: banner }

        Repeater {
            model: indexerModel
            delegate: HoltRow {
                required property var model
                thumbWidth: 0
                readonly property var result: page.testResults[model.indexerId]
                Text { text: model.name; font.family: Theme.fontCore; font.pixelSize: 14; font.weight: Font.Bold; color: Theme.ink; elide: Text.ElideRight; Layout.fillWidth: true }
                Meta { text: model.protocol + " · " + model.url; Layout.fillWidth: true }
                actions: [
                    Badge { tone: result ? (result.ok ? "available" : "error") : (model.indexerEnabled ? "pending" : "missing"); label: result ? (result.ok ? "reachable" : "failed") : (model.indexerEnabled ? "enabled" : "disabled") },
                    HoltButton { small: true; text: "Test"; onClicked: indexerModel.testIndexer(model.indexerId) },
                    HoltButton { kind: "quiet"; small: true; text: "Delete"; onClicked: indexerModel.deleteIndexer(model.indexerId) }
                ]
            }
        }

        EmptyState {
            visible: !indexerModel.loading && indexerModel.count === 0
            title: "No indexers yet"
            body: "Add a Torznab or Newznab endpoint (Jackett, Prowlarr, or a tracker's own API) and automation can start searching."
            actionText: "Add indexer"
            onAction: addDialog.open()
        }
    }

    HoltDialog {
        id: addDialog
        title: "Add an indexer"
        Field { label: "Name"; HoltTextField { id: nameField } }
        Field { label: "URL"; HoltTextField { id: urlField; placeholderText: "https://indexer.example/api" } }
        Field { label: "API key"; HoltTextField { id: apiKeyField; echoMode: TextInput.Password } }
        Field {
            label: "Protocol"
            Controls.ComboBox { id: protocolField; model: ["torznab", "newznab"]; font.family: Theme.fontCore }
        }
        footer: [
            HoltButton { kind: "quiet"; text: "Cancel"; onClicked: addDialog.close() },
            HoltButton {
                kind: "primary"; text: "Add"
                enabled: nameField.text.length > 0 && urlField.text.length > 0
                onClicked: { indexerModel.addIndexer(nameField.text, urlField.text, apiKeyField.text, protocolField.currentText); nameField.text = ""; urlField.text = ""; apiKeyField.text = ""; addDialog.close() }
            }
        ]
    }
}
