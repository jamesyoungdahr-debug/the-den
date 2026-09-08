import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root
    title: "The Den"
    width: 480
    height: 320

    pageStack.initialPage: Kirigami.Page {
        title: "Connection"

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.largeSpacing

            Kirigami.FormLayout {
                Layout.fillWidth: true

                Controls.TextField {
                    id: urlField
                    Kirigami.FormData.label: "Server URL:"
                    text: apiClient.baseUrl
                    onTextChanged: apiClient.baseUrl = text
                }
            }

            Controls.Button {
                text: "Connect"
                onClicked: apiClient.checkHealth()
            }

            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: true
                type: apiClient.connected ? Kirigami.MessageType.Positive : Kirigami.MessageType.Information
                text: apiClient.statusText
            }

            Controls.Button {
                text: "Indexers"
                enabled: apiClient.connected
                onClicked: root.pageStack.push(Qt.resolvedUrl("IndexersPage.qml"))
            }

            Item { Layout.fillHeight: true }
        }
    }
}
