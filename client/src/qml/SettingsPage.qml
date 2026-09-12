import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "holt"

// Settings as cards, bound to the backend's /api/settings record. Secrets show
// "set / not set" and are only sent when typed. Save lives in the top bar.
HoltPage {
    id: page
    objectName: "settingsPage"
    title: "Settings"
    padding: Theme.space4

    readonly property var s: settingsController.data

    Component.onCompleted: {
        settingsController.load()
        Controls.ApplicationWindow.window.pageAction = { text: "Save", trigger: function () { page.save() } }
    }
    Controls.StackView.onDeactivated: Controls.ApplicationWindow.window.pageAction = null
    Controls.StackView.onActivated: Controls.ApplicationWindow.window.pageAction = { text: "Save", trigger: function () { page.save() } }

    function num(text, fallback) { var n = Number(text); return isNaN(n) || text === "" ? fallback : n }
    function save() {
        settingsController.save({
            tmdb_api_key: tmdbField.text,
            movies_root: moviesRootField.text,
            tv_root: tvRootField.text,
            automation_interval_seconds: num(intervalField.text, 900),
            discord_webhook_url: discordField.text,
            downloads_root: downloadsRootField.text,
            torrent_port: num(portField.text, 6881),
            download_rate_limit_kib: num(downField.text, 0),
            upload_rate_limit_kib: num(upField.text, 0),
            seed_ratio_limit: num(ratioField.text, 0),
            seed_time_limit_minutes: num(seedTimeField.text, 0),
            plex_scan_interval_minutes: num(plexIntervalField.text, 30),
            request_movie_limit: num(movieLimitField.text, 10),
            request_series_limit: num(seriesLimitField.text, 5),
            request_limit_days: num(limitDaysField.text, 7),
        })
    }

    Connections {
        target: settingsController
        function onErrorOccurred(message) { banner.showError(message) }
        function onSaved() { banner.show("Saved. Torrent and automation changes are live already.", "positive"); tmdbField.text = ""; discordField.text = ""; Controls.ApplicationWindow.window.toast("Settings saved", "positive") }
    }

    component Section: GlassPanel {
        property string name: ""
        property string note: ""
        default property alias body: bodyCol.data
        Layout.fillWidth: true
        Layout.minimumWidth: 0
        Layout.preferredWidth: 400
        Layout.alignment: Qt.AlignTop
        ColumnLayout {
            width: parent.width
            spacing: Theme.space3
            RowLayout { Eyebrow { text: name } Item { Layout.fillWidth: true } Meta { text: note; visible: note !== "" } }
            ColumnLayout { id: bodyCol; spacing: Theme.space3; Layout.fillWidth: true }
        }
    }

    ColumnLayout {
        width: page.width - 2 * page.padding
        spacing: Theme.space3

        PageHeader { title: "Settings"; meta: "Blank fields fall back to the server's environment defaults. Secrets never show their value." }
        StatusBanner { id: banner }

        GridLayout {
            Layout.fillWidth: true
            columns: page.width > 1000 ? 2 : 1
            columnSpacing: Theme.space3
            rowSpacing: Theme.space3

            Section {
                name: "Library"
                Field { label: "TMDB API key · " + (page.s.has_tmdb_api_key ? "set" : "using the built-in key"); HoltTextField { id: tmdbField; echoMode: TextInput.Password; placeholderText: "leave blank to keep the current key" } }
                RowLayout {
                    spacing: Theme.space3
                    Field { label: "Movies folder"; HoltTextField { id: moviesRootField; text: page.s.movies_root || "" } }
                    Field { label: "TV folder"; HoltTextField { id: tvRootField; text: page.s.tv_root || "" } }
                }
            }

            Section {
                name: "Torrent client"; note: "built in"
                Field { label: "Downloads folder"; hint: "Finished files are hard-linked into the library so torrents keep seeding."; HoltTextField { id: downloadsRootField; text: page.s.downloads_root || "" } }
                RowLayout {
                    spacing: Theme.space3
                    Field { label: "Listen port"; HoltTextField { id: portField; text: page.s.torrent_port !== undefined ? String(page.s.torrent_port) : ""; validator: IntValidator { bottom: 1024; top: 65535 } } }
                    Field { label: "Down KiB/s (0 = none)"; HoltTextField { id: downField; text: page.s.download_rate_limit_kib !== undefined ? String(page.s.download_rate_limit_kib) : ""; validator: IntValidator { bottom: 0 } } }
                    Field { label: "Up KiB/s (0 = none)"; HoltTextField { id: upField; text: page.s.upload_rate_limit_kib !== undefined ? String(page.s.upload_rate_limit_kib) : ""; validator: IntValidator { bottom: 0 } } }
                }
                RowLayout {
                    spacing: Theme.space3
                    Field { label: "Seed ratio (0 = forever)"; HoltTextField { id: ratioField; text: page.s.seed_ratio_limit !== undefined ? String(page.s.seed_ratio_limit) : "" } }
                    Field { label: "Seed minutes (0 = none)"; HoltTextField { id: seedTimeField; text: page.s.seed_time_limit_minutes !== undefined ? String(page.s.seed_time_limit_minutes) : ""; validator: IntValidator { bottom: 0 } } }
                }
            }

            Section {
                name: "Automation"
                Field { label: "Check interval (seconds)"; hint: "How often The Den advances downloads, imports finished ones, and searches for what's missing."; HoltTextField { id: intervalField; text: page.s.automation_interval_seconds !== undefined ? String(page.s.automation_interval_seconds) : ""; validator: IntValidator { bottom: 60 } } }
            }

            Section {
                name: "Requests"; note: "quotas for non-admins"
                RowLayout {
                    spacing: Theme.space3
                    Field { label: "Movies (0 = unlimited)"; HoltTextField { id: movieLimitField; text: page.s.request_movie_limit !== undefined ? String(page.s.request_movie_limit) : ""; validator: IntValidator { bottom: 0 } } }
                    Field { label: "Series"; HoltTextField { id: seriesLimitField; text: page.s.request_series_limit !== undefined ? String(page.s.request_series_limit) : ""; validator: IntValidator { bottom: 0 } } }
                    Field { label: "Window (days)"; HoltTextField { id: limitDaysField; text: page.s.request_limit_days !== undefined ? String(page.s.request_limit_days) : ""; validator: IntValidator { bottom: 1 } } }
                }
                Meta { text: "Per-person limits are set on the web Users page. Admins have no quota."; Layout.fillWidth: true; wrapMode: Text.WordWrap; elide: Text.ElideNone }
            }

            Section {
                name: "Notifications"; note: "optional"
                Field { label: "Discord webhook · " + (page.s.has_discord_webhook ? "set" : "not set"); HoltTextField { id: discordField; echoMode: TextInput.Password; placeholderText: "leave blank to keep the current value" } }
            }

            Section {
                name: "Plex"
                note: page.s.has_plex_token ? "connected as " + (page.s.plex_owner_username || "owner") : "not connected"
                Meta { text: page.s.has_plex_token ? ("Server: " + (page.s.plex_server_name || "not chosen") + " · last scan " + (page.s.plex_last_scan_result || "never")) : "Connect the owner account from the web Settings page; the client can then scan on the interval below."; Layout.fillWidth: true; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                RowLayout {
                    spacing: Theme.space3
                    Field { label: "Library scan every (minutes)"; Layout.maximumWidth: 240; HoltTextField { id: plexIntervalField; text: page.s.plex_scan_interval_minutes !== undefined ? String(page.s.plex_scan_interval_minutes) : ""; validator: IntValidator { bottom: 5 } } }
                    HoltButton { text: "Scan now"; enabled: page.s.has_plex_token === true; Layout.alignment: Qt.AlignBottom; onClicked: settingsController.scanPlex() }
                }
            }

            Section {
                name: "Accounts"
                note: page.s.auth_required ? "sign-in required" : "sign-in optional"
                Meta { text: page.s.auth_required ? "Every page and API call needs a signed-in account; this client uses the API token from your profile." : "Anyone not signed in is an admin. Turn sign-in on from the web Settings page once everyone has an account."; Layout.fillWidth: true; wrapMode: Text.WordWrap; elide: Text.ElideNone }
            }
        }
    }
}
