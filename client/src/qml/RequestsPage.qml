import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "holt"
import "holt/Holt.js" as H

// The queue: filter chips, one glass row per request; admins approve / decline
// inline, users withdraw their own pending ones.
HoltPage {
    id: page
    objectName: "requestsPage"
    title: "Requests"
    padding: Theme.space4

    Component.onCompleted: requestsModel.refresh()

    Connections {
        target: requestsModel
        function onErrorOccurred(message) { banner.showError(message) }
        function onActionFinished(ok, message) { Controls.ApplicationWindow.window.toast(message, ok ? "positive" : "error"); if (!ok) banner.showError(message) }
    }

    readonly property var quota: apiClient.quota
    function quotaLine() {
        if (apiClient.isAdmin || !quota || !quota.movies) return ""
        var parts = []
        if (quota.movies.limit !== null && quota.movies.limit !== undefined) parts.push(quota.movies.remaining + " of " + quota.movies.limit + " movies left")
        if (quota.series.limit !== null && quota.series.limit !== undefined) parts.push(quota.series.remaining + " of " + quota.series.limit + " series left")
        return parts.length ? parts.join(" · ") + " this " + quota.days + " days" : ""
    }

    ColumnLayout {
        width: page.width - 2 * page.padding
        spacing: Theme.space3

        PageHeader {
            title: "Requests"
            meta: (apiClient.isAdmin ? requestsModel.pendingCount + " waiting on you · " + requestsModel.count + " shown" : "Your requests · " + requestsModel.count) + (page.quotaLine() ? " · " + page.quotaLine() : "")
            Chip { text: "All"; on: requestsModel.filter === "all"; onClicked: requestsModel.filter = "all" }
            Chip { text: "Pending"; badge: apiClient.isAdmin && requestsModel.pendingCount ? String(requestsModel.pendingCount) : ""; on: requestsModel.filter === "pending"; onClicked: requestsModel.filter = "pending" }
            Chip { text: "Approved"; on: requestsModel.filter === "approved"; onClicked: requestsModel.filter = "approved" }
            Chip { text: "Declined"; on: requestsModel.filter === "declined"; onClicked: requestsModel.filter = "declined" }
            Chip { text: "Available"; on: requestsModel.filter === "available"; onClicked: requestsModel.filter = "available" }
        }

        StatusBanner { id: banner }

        Repeater {
            model: requestsModel
            delegate: HoltRow {
                id: row
                required property var model
                required property int index
                thumb: H.posterUrl(model.posterPath)
                highlighted: model.status === "pending"
                opacity: model.status === "declined" ? 0.75 : 1
                onClicked: Controls.ApplicationWindow.window.openDetail(model.mediaType, model.tmdbId)

                RowLayout {
                    spacing: 8
                    Text { text: model.title; font.family: Theme.fontCore; font.pixelSize: 14; font.weight: Font.Bold; color: Theme.ink; elide: Text.ElideRight; Layout.maximumWidth: 420 }
                    Meta { text: model.year ? String(model.year) : "" }
                    Repeater { model: row.model.seasons; delegate: Chip { required property var modelData; text: "S" + H.pad(modelData); enabled: false; implicitHeight: 22; leftPadding: 8; rightPadding: 8 } }
                }
                Meta {
                    Layout.fillWidth: true
                    text: (model.mediaType === "movie" ? "Movie" : "Series")
                        + (model.status === "pending" ? " · requested " + H.relativeDay(model.createdAt) : "")
                        + (model.status === "approved" ? " · approved by " + (model.decidedBy || "admin") + (model.displayStatus !== "available" ? " · being looked for" : "") : "")
                        + (model.status === "available" ? " · available since " + H.relativeDay(model.availableAt) : "")
                        + (model.status === "declined" ? " · declined by " + (model.decidedBy || "admin") + (model.note ? " · “" + model.note + "”" : "") : "")
                }

                actions: [
                    RowLayout {
                        visible: apiClient.isAdmin && model.requester !== ""
                        spacing: 6
                        Avatar { initial: model.requesterInitial; size: 22 }
                        Text { text: model.requester; font.family: Theme.fontCore; font.pixelSize: 12; font.weight: Font.Bold; color: Theme.ink70 }
                    },
                    Badge { tone: H.statusBadge(model.displayStatus).tone; label: model.displayStatus; width: 110 },
                    HoltButton { visible: apiClient.isAdmin && model.status === "pending"; kind: "primary"; small: true; text: "Approve"; onClicked: requestsModel.approve(model.requestId) },
                    HoltButton { visible: apiClient.isAdmin && model.status === "pending"; kind: "quiet"; small: true; text: "Decline"; onClicked: { declineDialog.requestId = model.requestId; declineDialog.requestTitle = model.title; declineDialog.open() } },
                    HoltButton { visible: !apiClient.isAdmin && model.status === "pending" && model.requesterId === apiClient.me.id; kind: "quiet"; small: true; text: "Withdraw"; onClicked: requestsModel.remove(model.requestId) },
                    HoltButton { visible: model.seriesId > 0 && model.status !== "pending"; kind: "quiet"; small: true; text: "Episodes"; onClicked: Controls.ApplicationWindow.window.push("EpisodesPage.qml", { seriesId: model.seriesId, seriesTitle: model.title }) },
                    HoltButton { visible: apiClient.isAdmin && model.status !== "pending"; kind: "quiet"; small: true; text: "Remove"; onClicked: requestsModel.remove(model.requestId) }
                ]
            }
        }

        Repeater { visible: requestsModel.loading && requestsModel.count === 0; model: requestsModel.loading && requestsModel.count === 0 ? 3 : 0; delegate: Skeleton { Layout.fillWidth: true; height: 72 } }

        EmptyState {
            visible: !requestsModel.loading && requestsModel.count === 0
            title: apiClient.isAdmin && (requestsModel.filter === "all" || requestsModel.filter === "pending") ? "Nothing waiting on you" : "No requests here"
            body: apiClient.isAdmin ? "Everything's fine." : "Find something on Discover and hit Request."
            actionText: "Discover"
            onAction: Controls.ApplicationWindow.window.navigate("discover")
        }
    }

    HoltDialog {
        id: declineDialog
        property int requestId: 0
        property string requestTitle: ""
        title: "Decline " + requestTitle
        Field { label: "Reason (optional, shown to the requester)"; HoltTextField { id: noteField; placeholderText: "e.g. already on Plex under a different title" } }
        footer: [
            HoltButton { kind: "quiet"; text: "Cancel"; onClicked: declineDialog.close() },
            HoltButton { text: "Decline"; onClicked: { requestsModel.decline(declineDialog.requestId, noteField.text); noteField.text = ""; declineDialog.close() } }
        ]
    }
}
