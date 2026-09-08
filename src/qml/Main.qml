import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root
    title: "The Den"
    width: 480
    height: 380

    // App-wide brand override: Kirigami.Theme properties cascade to every descendant
    // Kirigami/QQC2 control (buttons, text fields, InlineMessage, ...) the same way
    // the web UI's --holt-* CSS custom properties cascade -- this is the QML
    // equivalent, not a hand-styled copy of it. (No colorSet override needed --
    // Kirigami.Theme.ColorSet has no "Custom" value; these direct property overrides
    // cascade to descendants on their own regardless of colorSet.)
    Kirigami.Theme.backgroundColor: Theme.deep
    Kirigami.Theme.textColor: Theme.ink
    Kirigami.Theme.highlightColor: Theme.current
    Kirigami.Theme.highlightedTextColor: Theme.deep
    Kirigami.Theme.positiveTextColor: Theme.healthy
    Kirigami.Theme.neutralTextColor: Theme.warning
    Kirigami.Theme.disabledTextColor: Theme.ink28

    pageStack.initialPage: Kirigami.Page {
        title: ""

        header: RowLayout {
            width: parent.width
            height: 56
            spacing: 13

            RingMark {
                markSize: 26
                Layout.leftMargin: Kirigami.Units.largeSpacing
            }

            Text {
                text: "The Den"
                font.family: Theme.fontCore
                font.weight: Font.Black
                font.pixelSize: 19
                color: Theme.ink
            }

            Item { Layout.fillWidth: true }
        }

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
                highlighted: true
                onClicked: apiClient.checkHealth()
            }

            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: true
                type: apiClient.connected ? Kirigami.MessageType.Positive : Kirigami.MessageType.Information
                text: apiClient.statusText
            }

            RowLayout {
                spacing: Kirigami.Units.smallSpacing

                Controls.Button {
                    text: "Indexers"
                    enabled: apiClient.connected
                    onClicked: root.pageStack.push(Qt.resolvedUrl("IndexersPage.qml"))
                }
                Controls.Button {
                    text: "Movies"
                    enabled: apiClient.connected
                    onClicked: root.pageStack.push(Qt.resolvedUrl("MoviesPage.qml"))
                }
                Controls.Button {
                    text: "TV"
                    enabled: apiClient.connected
                    onClicked: root.pageStack.push(Qt.resolvedUrl("SeriesPage.qml"))
                }
                Controls.Button {
                    text: "Downloads"
                    enabled: apiClient.connected
                    onClicked: root.pageStack.push(Qt.resolvedUrl("DownloadsPage.qml"))
                }
            }

            Item { Layout.fillHeight: true }
        }
    }
}
