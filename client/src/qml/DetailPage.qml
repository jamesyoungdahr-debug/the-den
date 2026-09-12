import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "holt"
import "holt/Holt.js" as H

// One movie or series: backdrop hero, facts, the request / add action, cast, seasons
// with per-season availability, the availability panel and recommendations.
HoltPage {
    id: page
    objectName: "detailPage"
    property string kind: "movie"
    property int tmdbId: 0
    readonly property var item: detailController.data
    // Derived from the record itself (not the controller flags) so it can never flip before `item` has updated.
    readonly property bool ready: item.tmdb_id === tmdbId && item.media_type === kind
    title: ready ? item.title : "Loading…"
    padding: 0

    Component.onCompleted: detailController.load(kind, tmdbId)

    Connections {
        target: detailController
        function onErrorOccurred(message) { banner.showError(message) }
        function onRequestFinished(ok, message) { ok ? banner.show(message, "positive") : banner.showError(message); if (ok) Controls.ApplicationWindow.window.toast(message, "positive") }
    }

    function myRequest() {
        if (!ready || !item.requests) return null
        for (var i = 0; i < item.requests.length; i++) if (item.requests[i].mine) return item.requests[i]
        return null
    }
    function seasonRow(n) {
        var lib = item.library && item.library.seasons ? item.library.seasons[String(n)] || item.library.seasons[n] : null
        var plex = item.availability && item.availability.plex && item.availability.plex.seasons ? (item.availability.plex.seasons[String(n)] || item.availability.plex.seasons[n]) : 0
        if (lib && lib.total && lib.have === lib.total) return { tone: "available", label: "complete" }
        if (plex) return { tone: "available", label: "on Plex" }
        if (lib && lib.have) return { tone: "partial", label: lib.have + "/" + lib.total }
        if (lib && lib.monitored) return { tone: "pending", label: "wanted" }
        if (item.requestable_seasons && item.requestable_seasons.indexOf(n) >= 0) return { tone: "missing", label: "not in library" }
        return { tone: "pending", label: "requested" }
    }
    function requestableSeasons() { return ready && item.requestable_seasons ? item.requestable_seasons : [] }

    ColumnLayout {
        width: page.width
        spacing: 0

        // ---- hero ----
        Item {
            Layout.fillWidth: true
            implicitHeight: heroContent.implicitHeight + 2 * Theme.space5
            clip: true
            Image { anchors.fill: parent; source: page.ready ? H.backdropUrl(page.item.backdrop_path) : ""; fillMode: Image.PreserveAspectCrop; asynchronous: true; sourceSize.width: 1280; opacity: 0.55 }
            Rectangle { anchors.fill: parent; gradient: Gradient { GradientStop { position: 0; color: Theme.scrimMid } GradientStop { position: 1; color: Theme.deep } } }

            RowLayout {
                id: heroContent
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: Theme.space5 }
                spacing: Theme.space5

                Rectangle {
                    width: page.width < 760 ? 120 : 180; height: Math.round(width * 1.5); radius: Theme.radiusLg; color: Theme.raised; clip: true
                    border.width: 1; border.color: Theme.glassBorderStrong
                    Image { anchors.fill: parent; source: page.ready ? H.posterUrl(page.item.poster_path) : ""; fillMode: Image.PreserveAspectCrop; asynchronous: true; sourceSize.width: 342 }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space2
                    Eyebrow { text: (page.kind === "movie" ? "Movie" : "Series") + (page.ready && page.item.tagline ? " · " + page.item.tagline : "") }
                    Text { text: page.ready ? page.item.title : "Loading…"; font.family: Theme.fontCore; font.weight: Font.Black; font.pixelSize: Math.min(Theme.sizeDisplay, Math.max(26, page.width / 26)); font.letterSpacing: -1.6; color: Theme.ink; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Meta {
                        Layout.fillWidth: true
                        text: !page.ready ? "" : [
                            page.item.year || "",
                            page.kind === "movie" && page.item.runtime ? Math.floor(page.item.runtime / 60) + "h " + H.pad(page.item.runtime % 60) + "m" : "",
                            page.kind === "tv" ? (page.item.number_of_seasons + " season" + (page.item.number_of_seasons === 1 ? "" : "s") + " · " + page.item.number_of_episodes + " episodes") : "",
                            page.item.rating ? "★ " + Number(page.item.rating).toFixed(1) + " (" + page.item.vote_count + ")" : ""
                        ].filter(function (s) { return s !== "" }).join(" · ")
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 6
                        Repeater { model: page.ready ? page.item.genres : []; delegate: Chip { required property var modelData; text: modelData; enabled: false } }
                    }
                    RowLayout {
                        spacing: 8
                        Layout.topMargin: 4
                        Badge { tone: page.ready ? H.statusBadge(page.item.status).tone : ""; label: page.ready ? H.statusBadge(page.item.status).label : "" }
                        Badge { visible: page.ready && page.item.on_plex; tone: "available"; label: "on Plex"; solid: true }

                        // the one action
                        HoltButton {
                            id: actionButton
                            kind: "primary"
                            visible: page.ready && text !== ""
                            enabled: apiClient.canBrowse
                            text: {
                                if (!page.ready) return ""
                                var mine = page.myRequest()
                                if (page.kind === "movie") {
                                    if (page.item.library) return ""
                                    if (page.item.availability && page.item.availability.available) return ""
                                    if (mine) return ""
                                    if (page.item.requests && page.item.requests.length) return ""
                                    return apiClient.isAdmin ? "Add to library" : "Request"
                                }
                                if (page.requestableSeasons().length) return apiClient.isAdmin ? "Add seasons" : "Request"
                                return ""
                            }
                            onClicked: page.kind === "movie" ? detailController.request([]) : seasonDialog.open()
                        }
                        Text {
                            visible: page.ready && actionButton.text === ""
                            font.family: Theme.fontCore; font.pixelSize: 13; font.weight: Font.Bold; color: Theme.ink55
                            text: {
                                if (!page.ready) return ""
                                var mine = page.myRequest()
                                if (mine) return "Requested · " + mine.status
                                if (page.item.requests && page.item.requests.length) return "Requested by " + page.item.requests[0].by
                                if (page.item.library) return page.kind === "movie" ? "In your library" : "In your library · " + page.item.library.have + " of " + page.item.library.total + " episodes"
                                if (page.item.availability && (page.item.availability.available || page.item.availability.plex)) return "Already on Plex"
                                return "Nothing to request"
                            }
                        }
                        HoltButton { visible: page.ready && page.kind === "tv" && page.item.library; small: true; text: "Episodes"; onClicked: Controls.ApplicationWindow.window.push("EpisodesPage.qml", { seriesId: page.item.library.id, seriesTitle: page.item.title }) }
                        HoltButton { visible: page.ready && page.item.trailer_key; kind: "quiet"; small: true; text: "Trailer ↗"; onClicked: Qt.openUrlExternally("https://www.youtube.com/watch?v=" + page.item.trailer_key) }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.margins: Theme.space4
            spacing: Theme.space4

            StatusBanner { id: banner }

            GridLayout {
                Layout.fillWidth: true
                columns: page.width > 900 ? 2 : 1
                columnSpacing: Theme.space4
                rowSpacing: Theme.space4

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.preferredWidth: 600
                    Layout.alignment: Qt.AlignTop
                    spacing: Theme.space4

                    Text { visible: page.ready && page.item.overview; text: page.ready ? page.item.overview : ""; font.family: Theme.fontCore; font.pixelSize: 15; lineHeight: 1.5; color: Theme.ink70; wrapMode: Text.WordWrap; Layout.fillWidth: true; Layout.maximumWidth: 760 }

                    // cast
                    ColumnLayout {
                        visible: page.ready && page.item.cast && page.item.cast.length > 0
                        spacing: Theme.space2
                        Eyebrow { text: "Cast"; accent: false }
                        ListView {
                            Layout.fillWidth: true
                            implicitHeight: 140
                            orientation: ListView.Horizontal
                            spacing: Theme.space3
                            clip: true
                            model: page.ready ? page.item.cast : []
                            delegate: ColumnLayout {
                                required property var modelData
                                width: 88
                                spacing: 4
                                Rectangle {
                                    width: 64; height: 64; radius: 32; color: Theme.raised; clip: true; Layout.alignment: Qt.AlignHCenter
                                    Image { anchors.fill: parent; source: H.profileUrl(modelData.profile_path); fillMode: Image.PreserveAspectCrop; asynchronous: true; sourceSize.width: 185; layer.enabled: true }
                                    Text { anchors.centerIn: parent; visible: !modelData.profile_path; text: modelData.name ? modelData.name.charAt(0) : "?"; font.family: Theme.fontCore; font.weight: Font.Black; font.pixelSize: 22; color: Theme.ink28 }
                                }
                                Text { text: modelData.name || ""; font.family: Theme.fontCore; font.pixelSize: 12; font.weight: Font.Bold; color: Theme.ink; elide: Text.ElideRight; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                                Meta { text: modelData.character || ""; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                            }
                        }
                    }

                    // seasons
                    ColumnLayout {
                        visible: page.kind === "tv" && page.ready && page.item.seasons && page.item.seasons.length > 0
                        spacing: Theme.space2
                        Layout.fillWidth: true
                        Eyebrow { text: "Seasons"; accent: false }
                        Repeater {
                            model: page.ready && page.kind === "tv" ? page.item.seasons.filter(function (s) { return s.season_number > 0 }) : []
                            delegate: HoltRow {
                                required property var modelData
                                thumb: H.posterUrl(modelData.poster_path)
                                thumbWidth: 32
                                Text { text: modelData.name || "Season " + modelData.season_number; font.family: Theme.fontCore; font.pixelSize: 14; font.weight: Font.Bold; color: Theme.ink; elide: Text.ElideRight; Layout.fillWidth: true }
                                Meta { text: modelData.episode_count + " episodes" + (modelData.air_date ? " · from " + modelData.air_date : "") }
                                actions: Badge { tone: page.seasonRow(modelData.season_number).tone; label: page.seasonRow(modelData.season_number).label }
                            }
                        }
                    }
                }

                // availability aside
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    Layout.minimumWidth: 280
                    Layout.maximumWidth: page.width > 900 ? 340 : -1
                    ColumnLayout {
                        width: parent.width
                        spacing: 10
                        Eyebrow { text: "Availability" }
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "The Den library"; font.family: Theme.fontCore; font.pixelSize: 13; color: Theme.ink70; Layout.fillWidth: true }
                            Badge {
                                readonly property var den: page.ready ? page.item.availability.den : null
                                tone: !den ? "missing" : (page.kind === "movie" ? (den.has_file ? "available" : "pending") : (den.total && den.have === den.total ? "available" : den.have ? "partial" : "pending"))
                                label: !den ? "not added" : (page.kind === "movie" ? (den.has_file ? "have" : "wanted") : (den.total && den.have === den.total ? "complete" : den.have ? den.have + "/" + den.total : "wanted"))
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Plex"; font.family: Theme.fontCore; font.pixelSize: 13; color: Theme.ink70; Layout.fillWidth: true }
                            Badge {
                                readonly property var plex: page.ready ? page.item.availability.plex : null
                                tone: plex ? "available" : "missing"
                                label: !plex ? "not on Plex" : (page.kind === "tv" && plex.seasons ? Object.keys(plex.seasons).length + " season" + (Object.keys(plex.seasons).length === 1 ? "" : "s") : "on Plex")
                            }
                        }
                        Repeater {
                            model: page.ready ? page.item.requests : []
                            delegate: RowLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                Text { text: "Request by " + (modelData.mine ? "you" : modelData.by) + (modelData.seasons && modelData.seasons.length ? "  " + modelData.seasons.map(function (n) { return "S" + H.pad(n) }).join(" ") : ""); font.family: Theme.fontCore; font.pixelSize: 13; color: Theme.ink70; Layout.fillWidth: true; elide: Text.ElideRight }
                                Badge { tone: modelData.status === "pending" ? "pending" : "processing"; label: modelData.status }
                            }
                        }
                        Meta { visible: page.ready && page.item.status === "wanted"; text: "Automation searches your indexers for wanted titles every cycle."; Layout.fillWidth: true; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                    }
                }
            }

            Rail {
                id: recRail
                title: "Recommended"
                subtitle: page.ready ? "because you looked at " + page.item.title : ""
                model: recModel
                onCardClicked: (t, id) => Controls.ApplicationWindow.window.openDetail(t, id)
            }
        }
    }

    // recommendations come inline with the detail; expose them through a tiny list model
    ListModel { id: recModel; property bool loading: false }
    onItemChanged: {
        recModel.clear()
        if (!ready || !item.recommendations) return
        for (var i = 0; i < item.recommendations.length; i++) {
            var r = item.recommendations[i]
            recModel.append({ mediaType: r.media_type, tmdbId: r.tmdb_id, title: r.title, year: r.year || 0, posterPath: r.poster_path || "", status: r.status || "", rating: r.rating || 0 })
        }
    }

    // ---- season picker ----
    HoltDialog {
        id: seasonDialog
        title: (apiClient.isAdmin ? "Add seasons of " : "Request seasons of ") + (page.ready ? page.item.title : "")
        property var picked: ({})
        onOpened: { picked = {}; var rs = page.requestableSeasons(); for (var i = 0; i < rs.length; i++) picked[rs[i]] = true; picked = picked }

        Repeater {
            model: page.ready && page.kind === "tv" ? page.item.seasons.filter(function (s) { return s.season_number > 0 }) : []
            delegate: HoltRow {
                required property var modelData
                readonly property bool can: page.requestableSeasons().indexOf(modelData.season_number) >= 0
                opacity: can ? 1 : 0.5
                Text { text: modelData.name || "Season " + modelData.season_number; font.family: Theme.fontCore; font.pixelSize: 13; font.weight: Font.Bold; color: Theme.ink; Layout.fillWidth: true }
                Meta { text: modelData.episode_count + " episodes" }
                actions: Controls.CheckBox {
                    enabled: can
                    checked: can ? (seasonDialog.picked[modelData.season_number] === true) : false
                    onToggled: { var p = seasonDialog.picked; p[modelData.season_number] = checked; seasonDialog.picked = p }
                }
            }
        }
        Meta { text: apiClient.isAdmin ? "Added straight to the library; only these seasons will be searched for." : "An admin approves requests; you'll see the status here and on Requests."; Layout.fillWidth: true; wrapMode: Text.WordWrap; elide: Text.ElideNone }

        footer: [
            HoltButton { kind: "quiet"; text: "Cancel"; onClicked: seasonDialog.close() },
            HoltButton {
                kind: "primary"; text: apiClient.isAdmin ? "Add selected" : "Request selected"
                onClicked: {
                    var seasons = []
                    for (var k in seasonDialog.picked) if (seasonDialog.picked[k]) seasons.push(Number(k))
                    if (seasons.length) detailController.request(seasons)
                    seasonDialog.close()
                }
            }
        ]
    }
}
