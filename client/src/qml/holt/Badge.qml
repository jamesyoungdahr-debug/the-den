import QtQuick

// Status badge: a dot + mono uppercase label. Tones match the web's .holt-badge-*:
// available (teal -- only ever means have/online), pending, processing, partial, error,
// missing. `solid` is the overlay variant used on poster cards.
Rectangle {
    id: badge
    property string tone: "missing"
    property string label: ""
    property bool solid: false

    readonly property color toneColor: ({
        available: Theme.badgeAvailable,
        pending: Theme.badgePending,
        processing: Theme.badgeProcessing,
        partial: Theme.badgePartial,
        error: Theme.badgeError,
        missing: Theme.badgeMissing,
    })[tone] || Theme.badgeMissing

    visible: label !== ""
    implicitWidth: row.implicitWidth + 16
    implicitHeight: 22
    radius: Theme.radiusPill
    color: solid ? Theme.glassBadgeSurface : "transparent"
    border.width: solid ? 1 : 0
    border.color: Theme.glassBorder

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6
        Rectangle {
            width: 6; height: 6; radius: 3
            anchors.verticalCenter: parent.verticalCenter
            color: badge.tone === "missing" ? Theme.badgeMissingDot : badge.toneColor
        }
        Text {
            text: badge.label.toUpperCase()
            font.family: Theme.fontMono
            font.pixelSize: 10
            font.letterSpacing: 1.2
            color: badge.solid ? Theme.ink : badge.toneColor
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
