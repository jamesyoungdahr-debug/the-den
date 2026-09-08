import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: "Settings"

    Component.onCompleted: settingsController.load()

    // No ListView.header involved here (single record, not a list) -- same reason
    // as CalendarPage.qml, so the M3 id-scoping bug's precondition doesn't apply.
    Connections {
        target: settingsController
        function onErrorOccurred(message) {
            statusBanner.text = "Error: " + message
            statusBanner.type = Kirigami.MessageType.Error
            statusBanner.visible = true
        }
        function onSaved() {
            statusBanner.text = "Saved."
            statusBanner.type = Kirigami.MessageType.Positive
            statusBanner.visible = true
            // Clear secret fields after a successful save -- they were sent, and the
            // backend never echoes them back, so an empty field correctly means
            // "leave alone" again on the next save.
            tmdbApiKeyField.text = ""
            qbitPasswordField.text = ""
            discordWebhookField.text = ""
        }
    }

    ColumnLayout {
        width: page.width
        spacing: Kirigami.Units.largeSpacing

        Kirigami.InlineMessage {
            id: statusBanner
            Layout.fillWidth: true
            visible: false
        }

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Controls.TextField {
                id: tmdbApiKeyField
                Kirigami.FormData.label: "TMDB API key (" + (settingsController.hasTmdbApiKey ? "set" : "not set") + "):"
                placeholderText: "leave blank to keep current value"
                echoMode: TextInput.Password
            }
            Controls.TextField {
                id: qbitUrlField
                Kirigami.FormData.label: "qBittorrent URL:"
                text: settingsController.qbitUrl
            }
            Controls.TextField {
                id: qbitUsernameField
                Kirigami.FormData.label: "qBittorrent username:"
                text: settingsController.qbitUsername
            }
            Controls.TextField {
                id: qbitPasswordField
                Kirigami.FormData.label: "qBittorrent password (" + (settingsController.hasQbitPassword ? "set" : "not set") + "):"
                placeholderText: "leave blank to keep current value"
                echoMode: TextInput.Password
            }
            Controls.TextField {
                id: moviesRootField
                Kirigami.FormData.label: "Movies library folder:"
                text: settingsController.moviesRoot
            }
            Controls.TextField {
                id: tvRootField
                Kirigami.FormData.label: "TV library folder:"
                text: settingsController.tvRoot
            }
            Controls.SpinBox {
                id: intervalField
                Kirigami.FormData.label: "Automation interval (seconds):"
                from: 60
                to: 86400
                value: settingsController.automationIntervalSeconds
            }
            Controls.TextField {
                id: discordWebhookField
                Kirigami.FormData.label: "Discord webhook (" + (settingsController.hasDiscordWebhook ? "set" : "not set") + "):"
                placeholderText: "leave blank to keep current value"
                echoMode: TextInput.Password
            }

            Controls.Button {
                text: "Save"
                highlighted: true
                onClicked: settingsController.save(
                    tmdbApiKeyField.text,
                    qbitUrlField.text,
                    qbitUsernameField.text,
                    qbitPasswordField.text,
                    moviesRootField.text,
                    tvRootField.text,
                    intervalField.value,
                    discordWebhookField.text
                )
            }
        }
    }
}
