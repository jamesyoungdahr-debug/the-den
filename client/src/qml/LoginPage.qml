import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "holt"

// Server URL + sign-in: "Sign in with Plex" (PIN flow in the system browser) first,
// local account second. Shown until the backend reports we may browse.
HoltPage {
    id: page
    objectName: "loginPage"
    title: "Sign in"
    padding: 0

    Connections {
        target: apiClient
        function onLoginFailed(message) { banner.showError(message) }
    }

    Item {
        implicitHeight: Math.max(card.implicitHeight + 2 * Theme.space6, page.height)

        GlassPanel {
            id: card
            strong: true
            width: Math.min(440, page.width - 2 * Theme.space4)
            anchors.centerIn: parent
            padding: Theme.space5

            ColumnLayout {
                width: parent.width
                spacing: Theme.space3

                RowLayout {
                    spacing: 12
                    RingMark { markSize: 34 }
                    ColumnLayout {
                        spacing: 0
                        Text { text: "The Den"; font.family: Theme.fontCore; font.weight: Font.Black; font.pixelSize: 26; font.letterSpacing: -1; color: Theme.ink }
                        Eyebrow { text: "part of HoltOS" }
                    }
                }

                StatusBanner { id: banner }

                Field {
                    label: "Server"
                    HoltTextField {
                        id: urlField
                        text: apiClient.baseUrl
                        placeholderText: "http://den.local:8686"
                        onAccepted: { apiClient.baseUrl = text; apiClient.checkHealth() }
                    }
                }
                RowLayout {
                    spacing: 8
                    HoltButton { text: apiClient.connected ? "Reconnect" : "Connect"; kind: apiClient.connected ? "secondary" : "primary"; enabled: !apiClient.busy; onClicked: { apiClient.baseUrl = urlField.text; apiClient.checkHealth() } }
                    Badge {
                        tone: apiClient.connected ? "available" : (apiClient.busy ? "processing" : "missing")
                        label: apiClient.connected ? "connected" : (apiClient.busy ? "checking" : "offline")
                    }
                    Item { Layout.fillWidth: true }
                }
                Meta { visible: !apiClient.connected && apiClient.statusText !== "Not connected"; text: apiClient.statusText; Layout.fillWidth: true; wrapMode: Text.WordWrap; elide: Text.ElideNone }

                // ---- sign-in, once connected ----
                ColumnLayout {
                    visible: apiClient.connected
                    Layout.fillWidth: true
                    spacing: Theme.space3

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.glassBorder }

                    ColumnLayout {
                        visible: !apiClient.plexWaiting
                        spacing: 8
                        Layout.fillWidth: true
                        HoltButton {
                            Layout.fillWidth: true
                            kind: "primary"
                            text: "Sign in with Plex"
                            enabled: !apiClient.busy
                            onClicked: apiClient.startPlexLogin()
                        }
                        Meta { text: "Opens plex.tv in your browser; come back here once you've approved it."; Layout.fillWidth: true; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                    }
                    GlassPanel {
                        visible: apiClient.plexWaiting
                        Layout.fillWidth: true
                        ColumnLayout {
                            width: parent.width
                            spacing: 8
                            Eyebrow { text: "Waiting for plex.tv" }
                            Text { text: "Approve the link in your browser. Your code is " + apiClient.plexCode + "."; font.family: Theme.fontCore; font.pixelSize: 13; color: Theme.ink70; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            RowLayout {
                                HoltButton { small: true; text: "Open plex.tv again"; onClicked: apiClient.openPlexAuth() }
                                HoltButton { small: true; kind: "quiet"; text: "Cancel"; onClicked: apiClient.cancelPlexLogin() }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.glassBorder }
                        Eyebrow { text: "or a local account"; accent: false }
                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.glassBorder }
                    }

                    Field { label: "Username"; HoltTextField { id: userField; onAccepted: passField.forceActiveFocus() } }
                    Field { label: "Password"; HoltTextField { id: passField; echoMode: TextInput.Password; onAccepted: apiClient.login(userField.text, passField.text) } }
                    HoltButton { text: "Sign in"; enabled: !apiClient.busy && userField.text.length > 0 && passField.text.length > 0; onClicked: apiClient.login(userField.text, passField.text) }

                    Meta {
                        visible: apiClient.connected && !apiClient.authRequired && !apiClient.signedIn
                        text: "This server doesn't require sign-in; you're browsing as an anonymous admin."
                        Layout.fillWidth: true; wrapMode: Text.WordWrap; elide: Text.ElideNone
                    }
                    HoltButton { visible: apiClient.canBrowse && !apiClient.signedIn; kind: "quiet"; text: "Continue without signing in"; onClicked: Controls.ApplicationWindow.window.navigate("discover") }
                }
            }
        }
    }
}
