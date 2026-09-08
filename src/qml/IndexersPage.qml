import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: "Indexers"

    Component.onCompleted: indexerModel.refresh()

    Connections {
        target: indexerModel
        function onErrorOccurred(message) {
            statusBanner.text = "Error: " + message
            statusBanner.type = Kirigami.MessageType.Error
            statusBanner.visible = true
        }
        function onTestResult(indexerId, ok, message) {
            statusBanner.text = (ok ? "Test OK: " : "Test failed: ") + message
            statusBanner.type = ok ? Kirigami.MessageType.Positive : Kirigami.MessageType.Warning
            statusBanner.visible = true
        }
    }

    ListView {
        id: listView
        model: indexerModel

        header: ColumnLayout {
            width: listView.width
            spacing: Kirigami.Units.largeSpacing

            Kirigami.InlineMessage {
                id: statusBanner
                Layout.fillWidth: true
                visible: false
            }

            Kirigami.FormLayout {
                Layout.fillWidth: true

                Controls.TextField {
                    id: nameField
                    Kirigami.FormData.label: "Name:"
                }
                Controls.TextField {
                    id: urlField
                    Kirigami.FormData.label: "URL:"
                    placeholderText: "https://indexer.example/api"
                }
                Controls.TextField {
                    id: apiKeyField
                    Kirigami.FormData.label: "API key:"
                    echoMode: TextInput.Password
                }
                Controls.ComboBox {
                    id: protocolField
                    Kirigami.FormData.label: "Protocol:"
                    model: ["torznab", "newznab"]
                }
                Controls.Button {
                    text: "Add indexer"
                    enabled: nameField.text.length > 0 && urlField.text.length > 0
                    onClicked: {
                        indexerModel.addIndexer(nameField.text, urlField.text, apiKeyField.text, protocolField.currentText)
                        nameField.text = ""
                        urlField.text = ""
                        apiKeyField.text = ""
                    }
                }
            }

            Kirigami.Separator { Layout.fillWidth: true }
        }

        delegate: Kirigami.SwipeListItem {
            width: listView.width
            contentItem: RowLayout {
                spacing: Kirigami.Units.largeSpacing

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: name
                        font.family: Theme.fontCore
                        font.weight: Font.Bold
                        font.pixelSize: 13
                        color: Theme.ink
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    Text {
                        text: protocol + " — " + url
                        font.family: Theme.fontMono
                        font.pixelSize: 10
                        color: Theme.ink42
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }

                StatusPill {
                    label: indexerEnabled ? "enabled" : "disabled"
                    tone: indexerEnabled ? "healthy" : "idle"
                }
            }
            actions: [
                Kirigami.Action { text: "Test"; onTriggered: indexerModel.testIndexer(indexerId) },
                Kirigami.Action { text: "Delete"; onTriggered: indexerModel.deleteIndexer(indexerId) }
            ]
        }
    }
}
